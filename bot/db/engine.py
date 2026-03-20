from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession


def create_db_engine(database_url: str):
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory
