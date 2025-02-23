#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import binascii

class MSSQLEXEC:

    def __init__(self, connection):
        self.mssql_conn = connection
        self.outputBuffer = ''

    def execute(self, command, output=False):
        try:
            self.enable_xp_cmdshell()
            self.mssql_conn.sql_query("exec master..xp_cmdshell '{}'".format(command))

            if output:
                self.mssql_conn.printReplies()
                self.mssql_conn.colMeta[0]['TypeData'] = 80*2
                self.mssql_conn.printRows()
                self.outputBuffer = self.mssql_conn._MSSQL__rowsPrinter.getMessage()
                if len(self.outputBuffer):
                    self.outputBuffer = self.outputBuffer.split('\n', 2)[2]

            self.disable_xp_cmdshell()
            return self.outputBuffer

        except Exception as e:
            logging.debug('Error executing command via mssqlexec: {}'.format(e))

    def enable_xp_cmdshell(self):
        self.mssql_conn.sql_query("exec master.dbo.sp_configure 'show advanced options',1;RECONFIGURE;exec master.dbo.sp_configure 'xp_cmdshell', 1;RECONFIGURE;")

    def disable_xp_cmdshell(self):
        self.mssql_conn.sql_query("exec sp_configure 'xp_cmdshell', 0 ;RECONFIGURE;exec sp_configure 'show advanced options', 0 ;RECONFIGURE;")

    def enable_ole(self):
        self.mssql_conn.sql_query("exec master.dbo.sp_configure 'show advanced options',1;RECONFIGURE;exec master.dbo.sp_configure 'Ole Automation Procedures', 1;RECONFIGURE;")

    def disable_ole(self):
        self.mssql_conn.sql_query("exec master.dbo.sp_configure 'show advanced options',1;RECONFIGURE;exec master.dbo.sp_configure 'Ole Automation Procedures', 0;RECONFIGURE;")

    def put_file(self, data, remote):
        try:
            self.enable_ole()
            hexdata = data.hex()
            self.mssql_conn.sql_query("DECLARE @ob INT;"
                                        "EXEC sp_OACreate 'ADODB.Stream', @ob OUTPUT;"
                                        "EXEC sp_OASetProperty @ob, 'Type', 1;"
                                        "EXEC sp_OAMethod @ob, 'Open';"
                                        "EXEC sp_OAMethod @ob, 'Write', NULL, 0x{};"
                                        "EXEC sp_OAMethod @ob, 'SaveToFile', NULL, '{}', 2;"
                                        "EXEC sp_OAMethod @ob, 'Close';"
                                        "EXEC sp_OADestroy @ob;".format(hexdata, remote))
            self.disable_ole()
        except Exception as e:
            logging.debug('Error uploading via mssqlexec: {}'.format(e))

    def file_exists(self, remote):
        try:
            res = self.mssql_conn.batch("DECLARE @r INT; EXEC master.dbo.xp_fileexist '{}', @r OUTPUT; SELECT @r as n".format(remote))[0]['n']
            return res == 1
        except:
            return False

    def get_file(self, remote, local):
        try:
            self.mssql_conn.sql_query("SELECT * FROM OPENROWSET(BULK N'{}', SINGLE_BLOB) rs".format(remote))
            data = self.mssql_conn.rows[0]['BulkColumn']

            with open(local, 'wb+') as f:
                f.write(binascii.unhexlify(data))

        except Exception as e:
            logging.debug('Error downloading via mssqlexec: {}'.format(e))