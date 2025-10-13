# -*- coding: utf-8 -*-
"""Simulation of a machine that manufactures pieces, publishing events to RabbitMQ."""
import asyncio
import logging
from random import randint
import pika
from pika.exchange_type import ExchangeType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import ProgrammingError, OperationalError
from app.sql import crud
from app.sql.models import Piece
import time
from pika.exceptions import AMQPConnectionError
logger = logging.getLogger(__name__)
logger.debug("Machine logger set.")
import ssl

class Machine:
    """Piece manufacturing machine simulator that publishes events to RabbitMQ."""
    STATUS_WAITING = "Waiting"
    STATUS_CHANGING_PIECE = "Changing Piece"
    STATUS_WORKING = "Working"
    __manufacturing_queue = asyncio.Queue()
    __stop_machine = False
    working_piece = None
    status = STATUS_WAITING

    def __init__(self, session_factory):
        """Initialize machine and connect to RabbitMQ."""
        self._session_factory = session_factory

        # --- RabbitMQ setup ---
        try:
            self._amqp_url = "amqp://guest:guest@localhost:5672/%2F"
            self._exchange = "machine.events"
            context = ssl.create_default_context(cafile="/app/ssl/ca_cert.pem")
            
            for i in range(10):
                try:
                    self._connection = pika.BlockingConnection(
                        pika.ConnectionParameters(
                            host='rabbitmq',
                            port=5671,
                            virtual_host='/',
                            credentials=pika.PlainCredentials('guest', 'guest'),
                            ssl_options=pika.SSLOptions(context)
                        )
                    )
                    break
                except pika.exceptions.AMQPConnectionError:
                    print("RabbitMQ not ready, retrying...")
                    time.sleep(2)
            else:
                logger.error("Failed to connect to RabbitMQ after several attempts.")
                
            self._channel = self._connection.channel()
            self._channel.exchange_declare(exchange=self._exchange, exchange_type=ExchangeType.topic)
            logger.info("Connected to RabbitMQ over TLS and exchange declared.")

        except Exception as e:
            logger.error(f"Could not connect to RabbitMQ: {e}")
            self._connection = None
            self._channel = None

    @classmethod
    async def create(cls, session_factory):
        """Initialize machine asynchronously and load queued pieces."""
        logger.info("AsyncMachine initialized")
        self = Machine(session_factory)
        asyncio.create_task(self.manufacturing_coroutine())
        await self.reload_queue_from_database()
        return self

    async def reload_queue_from_database(self):
        """Reload queue from database, to reload data when the system has been rebooted."""
        async with self._session_factory() as db:
            manufacturing_piece = await Machine.get_manufacturing_piece(db)
            if manufacturing_piece:
                await self.add_piece_to_queue(manufacturing_piece)

            queued_pieces = await Machine.get_queued_pieces(db)
            if queued_pieces:
                await self.add_pieces_to_queue(queued_pieces)
            await db.close()

    @staticmethod
    async def get_manufacturing_piece(db: AsyncSession):
        """Gets the manufacturing piece from the database."""
        try:
            manufacturing_pieces = await crud.get_piece_list_by_status(db, Piece.STATUS_MANUFACTURING)
            if manufacturing_pieces and manufacturing_pieces[0]:
                return manufacturing_pieces[0]
        except (ProgrammingError, OperationalError):
            logger.error("Error getting Manufacturing Piece at startup.")
        return None

    @staticmethod
    async def get_queued_pieces(db: AsyncSession):
        """Get all queued pieces from the database."""
        try:
            queued_pieces = await crud.get_piece_list_by_status(db, Piece.STATUS_QUEUED)
            return queued_pieces
        except (ProgrammingError, OperationalError):
            logger.error("Error getting Queued Pieces at startup.")
            return []

    async def manufacturing_coroutine(self) -> None:
        """Coroutine that manufactures queued pieces one by one."""
        while not self.__stop_machine:
            if self.__manufacturing_queue.empty():
                self.status = self.STATUS_WAITING
            piece_id = await self.__manufacturing_queue.get()
            await self.create_piece(piece_id)
            self.__manufacturing_queue.task_done()

    async def create_piece(self, piece_id: int):
        """Simulates piece manufacturing."""
        async with self._session_factory() as db:
            await self.update_working_piece(piece_id, db)
            await self.working_piece_to_manufacturing(db)
            await db.close()

        self.publish_event("piece.started", {"piece_id": piece_id})

        await asyncio.sleep(randint(5, 20))

        async with self._session_factory() as db:
            await self.working_piece_to_finished(db)
            await db.close()

        self.publish_event("piece.finished", {"piece_id": piece_id})

        self.working_piece = None

    def publish_event(self, topic: str, payload: dict):
        """Publica un mensaje (evento) a RabbitMQ usando 'topic'."""
        if not self._channel:
            logger.warning(f"Cannot publish event {topic}: no RabbitMQ connection.")
            return
        try:
            import json
            body = json.dumps(payload)
            self._channel.basic_publish(
                exchange=self._exchange,
                routing_key=topic,
                body=body.encode("utf-8")
            )
            logger.info(f"Published event '{topic}': {body}")
        except Exception as e:
            logger.error(f"Error publishing event {topic}: {e}")

    async def update_working_piece(self, piece_id: int, db: AsyncSession):
        piece = await crud.get_piece(db, piece_id)
        self.working_piece = piece.as_dict()

    async def working_piece_to_manufacturing(self, db: AsyncSession):
        self.status = Machine.STATUS_WORKING
        try:
            await crud.update_piece_status(db, self.working_piece['id'], Piece.STATUS_MANUFACTURING)
        except Exception as exc:
            logger.error(f"Could not update status to manufacturing: {exc}")

    async def working_piece_to_finished(self, db: AsyncSession):
        logger.debug("Working piece finished.")
        self.status = Machine.STATUS_CHANGING_PIECE
        piece = await crud.update_piece_status(db, self.working_piece['id'], Piece.STATUS_MANUFACTURED)
        self.working_piece = piece.as_dict()
        piece = await crud.update_piece_manufacturing_date_to_now(db, self.working_piece['id'])
        self.working_piece = piece.as_dict()
        return "Finished"

    async def add_pieces_to_queue(self, pieces):
        for piece in pieces:
            await self.add_piece_to_queue(piece)

    async def add_piece_to_queue(self, piece):
        await self.__manufacturing_queue.put(piece.id)

    async def list_queued_pieces(self):
        piece_list = list(self.__manufacturing_queue.__dict__['_queue'])
        return piece_list
