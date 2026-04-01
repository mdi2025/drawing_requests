#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import pymysql.cursors
import sys
import threading


class DBHandler:
    def __init__(self):
        self.host = "192.51.11.206"
        self.user = "erp"
        self.password = "erpdeveloper"
        self.dbname = "mdiacc"
        self.conn = None
        self.lock = threading.Lock()

    def warm_up(self):
        """Pre-establishes the database connection in a background thread."""

        def connect():
            try:
                self.get_connection()
                print("Database connection warmed up successfully.")
            except Exception as e:
                print("Failed to warm up database connection: {}".format(e))

        thread = threading.Thread(target=connect)
        thread.daemon = True
        thread.start()

    def get_connection(self):
        """Returns a database connection."""
        with self.lock:
            try:
                if self.conn is None or not self.conn.open:
                    self.conn = pymysql.connect(
                        host=self.host,
                        user=self.user,
                        passwd=self.password,
                        db=self.dbname,
                        charset="utf8",
                        cursorclass=pymysql.cursors.DictCursor,
                        autocommit=True,
                    )
                return self.conn
            except pymysql.Error as e:
                print("Error connecting to MySQL Database: {}".format(e))
                return None

    def fetch_all(self, query, params=None):
        """Executes a query and returns all results."""
        with self.lock:
            conn = self._get_connection_no_lock()
            if not conn:
                return []

            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
            except pymysql.Error as e:
                print("Error executing query: {}".format(e))
                return []
            finally:
                cursor.close()

    def _get_connection_no_lock(self):
        """Internal helper to get connection without acquiring lock."""
        try:
            if self.conn is None or not self.conn.open:
                self.conn = pymysql.connect(
                    host=self.host,
                    user=self.user,
                    passwd=self.password,
                    db=self.dbname,
                    charset="utf8",
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True,
                )
            return self.conn
        except pymysql.Error as e:
            print("Error connecting to MySQL Database: {}".format(e))
            return None

    def execute_query(self, query, params=None):
        """Executes a query (INSERT, UPDATE, DELETE)."""
        with self.lock:
            conn = self._get_connection_no_lock()
            if not conn:
                return False

            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return True
            except pymysql.Error as e:
                print("Error executing query: {}".format(e))
                conn.rollback()
                return False
            finally:
                cursor.close()

    def execute_insert(self, query, params=None):
        """Executes an INSERT query and returns the last insert ID."""
        with self.lock:
            conn = self._get_connection_no_lock()
            if not conn:
                return None

            cursor = conn.cursor()
            try:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                last_id = cursor.lastrowid
                return last_id
            except pymysql.Error as e:
                print("Error executing query: {}".format(e))
                return None
            finally:
                cursor.close()

    def close(self):
        """Closes the connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


# Global instance for easy access
db = DBHandler()
