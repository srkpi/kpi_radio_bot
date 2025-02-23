from typing import Any, Generic, Optional, Sequence, Tuple, Type, TypeVar
from uuid import UUID

from sqlalchemy import (
    BinaryExpression,
    ColumnElement,
    ColumnOperators,
    Select,
    delete,
    exists,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.interfaces import ORMOption
from sqlalchemy.sql.base import ExecutableOption

from app.bot.models import Base

Model = TypeVar("Model", bound=Base)


class BaseRepository(Generic[Model]):
    __model__: Type[Model]
    __session: AsyncSession

    def __init__(self, model: Type[Model], session: AsyncSession):
        self.__model__ = model
        self._session = session

    async def get_count(
        self, *expressions: BinaryExpression[Any] | ColumnOperators
    ) -> Optional[int]:
        query = select(func.count()).select_from(self.__model__)
        query = self._set_filter(query, expressions)
        return await self._session.scalar(query)

    async def create(self, model: Model) -> Model:
        self._session.add(model)
        return model

    async def merge(self, model: Model) -> Model:
        await self._session.merge(model)
        return model

    async def get(
        self, pk: UUID, options: Optional[Sequence[ORMOption]] = None
    ) -> Model | None:
        return await self._session.get(self.__model__, pk, options=options)

    async def update(
        self, *expressions: BinaryExpression[Any] | ColumnOperators, **kwargs: Any
    ) -> Sequence[Model]:
        query = (
            update(self.__model__)
            .values(**kwargs)
            .execution_options(synchronize_session="evaluate")
            .returning(self.__model__)
        )
        query = self._set_filter(query, expressions)
        return (await self._session.scalars(query)).all()

    async def delete(
        self, *expressions: BinaryExpression[Any] | ColumnOperators
    ) -> None:
        query = delete(self.__model__)
        query = self._set_filter(query, expressions)
        await self._session.execute(query)

    async def find(
        self,
        *expressions: BinaryExpression[Any] | ColumnOperators,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        options: Optional[Sequence[ExecutableOption]] = None,
        order: Optional[Sequence[ColumnElement[Model]]] = None,
    ) -> Sequence[Model]:
        query = select(self.__model__)
        query = self._set_filter_with_additions(
            query, expressions, limit, offset, options, order
        )
        return (await self._session.scalars(query)).all()

    async def find_one(
        self,
        *expressions: BinaryExpression[Any] | ColumnOperators,
        offset: Optional[int] = None,
        options: Optional[Sequence[ExecutableOption]] = None,
        order: Optional[Sequence[ColumnElement[Model]]] = None,
    ) -> Optional[Model]:
        query = select(self.__model__).limit(1)
        query = self._set_filter_with_additions(
            query, expressions, 1, offset, options, order
        )
        return (await self._session.scalars(query)).first()

    @staticmethod
    def _set_filter(
        query: Any, expressions: Tuple[BinaryExpression[Any] | ColumnOperators, ...]
    ) -> Any:
        if expressions is not None:
            query = query.where(*expressions)
        return query

    @staticmethod
    def _set_additions(
        query: Select[Tuple[Model]],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        options: Optional[Sequence[ExecutableOption]] = None,
        order: Optional[Sequence[ColumnElement[Model]]] = None,
    ) -> Any:
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        if options is not None:
            query = query.options(*options)
        if order is not None:
            query = query.order_by(*order)
        return query

    def _set_filter_with_additions(
        self,
        query: Any,
        expressions: Tuple[BinaryExpression[Any] | ColumnOperators, ...] = (),
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        options: Optional[Sequence[ExecutableOption]] = None,
        order: Optional[Sequence[ColumnElement[Model]]] = None,
    ) -> Any:
        query = self._set_filter(query, expressions)
        query = self._set_additions(query, limit, offset, options, order)
        return query

    async def check_exists(self, *expressions: BinaryExpression[Any]) -> bool:
        query = exists(self.__model__.id).select()
        query = self._set_filter_with_additions(query, expressions, 1)
        return await self._session.scalar(query) or False
