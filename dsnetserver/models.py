from sqlalchemy import Table, Column, Integer, DateTime, Text, LargeBinary, String, MetaData

# Database table definitions.
metadata = MetaData()

broadcast_query_table = Table(
    "broadcast_query",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("received_at", DateTime(), index=True),
    Column("message", LargeBinary, nullable=False),
)

pigeonhole_message_table = Table(
    "pigeonhole_message",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("received_at", DateTime(), index=True),
    Column("message", LargeBinary, nullable=False),
    Column("address", String(64), index=True, nullable=False),
)
