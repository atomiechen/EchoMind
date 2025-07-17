from pathlib import Path
from sqlalchemy import make_url
from sqlmodel import SQLModel, create_engine

from app.config import settings


engine = create_engine(settings.db_url, connect_args={"check_same_thread": False})


def init_db() -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines

    from app import models as models

    # check if sqlite and make necessary dirs
    url = make_url(settings.db_url)
    if url.get_backend_name().startswith("sqlite"):
        db_path = url.database
        if (
            db_path
            and not db_path.startswith(":memory:")
            and not db_path.startswith("file:")
        ):
            p = Path(db_path)
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)

    # This works because the models are already imported and registered from app.models
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
