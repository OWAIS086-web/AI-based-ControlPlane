"""
Single Prisma client instance shared across the application.
Call `connect()` on startup and `disconnect()` on shutdown.
"""
from prisma import Prisma

db = Prisma()
