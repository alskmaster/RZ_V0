from .base_collector import BaseCollector
from flask import current_app

class AgentStatusCollector(BaseCollector):
    """Conta hosts por status de disponibilidade do agente (available: 1 OK, 0 DOWN, 2 UNKNOWN)."""
    def collect(self, all_hosts, period):
        try:
            body = {
                'jsonrpc':'2.0','method':'host.get',
                'params':{
                    'output':['hostid','name','available']
                },
                'auth': self.token,
                'id':1
            }
            from app.zabbix_api import fazer_request_zabbix
            res = fazer_request_zabbix(body, self.url)
            ok=down=unknown=0
            if isinstance(res, list):
                for h in res:
                    av = str(h.get('available','2'))
                    if av=='1': ok+=1
                    elif av=='0': down+=1
                    else: unknown+=1
            return self.render('agent_status', {'ok': ok, 'down': down, 'unknown': unknown})
        except Exception as e:
            current_app.logger.error('AgentStatusCollector error', exc_info=True)
            return self.render('agent_status', {'error':'Falha ao consultar host.get'})

