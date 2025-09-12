import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from collections import defaultdict
from dotenv import load_dotenv
import argparse
import copy
import datetime as dt
import json
import logging
import pandas as pd
import re
import requests
import time

import urllib3
urllib3.disable_warnings()

load_dotenv(override=True)

# ------------------- LOGGING -------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# ------------------- ARGUMENTOS -------------------
parser = argparse.ArgumentParser(
    description='Gera relatório de causa raiz consultando a API do Softdesk com base nos acks de incidentes no Zabbix.',
)
parser.add_argument('-m', '--mes', help='Mês de referência no formato "YYYY-MM".')
parser.add_argument('-s', '--saida', default='relatorio_causa_raiz.md', help='Arquivo de saída (Markdown).')
parser.add_argument('-g', '--groupids', help='ID(s) de grupo(s) de hosts.')
parser.add_argument('-sev', '--severidade', help='Severidade mínima para eventos (default=1).')
parser.add_argument('-fs', '--filtrosla', help='Porcentagem de SLA desejada para exibição de análise de causa raiz.')
parser.add_argument('-fk', '--filtrokey', nargs='+', help='Key(s) da(s) métrica(s) desejada(s), separadas por espaço se maior que 1.')
parser.add_argument('-det', '--determinante', help='Key determinante para o SLA do host.')
args = parser.parse_args()

# ------------------- CONFIG -------------------
AGORA = dt.datetime.now()
URL_RAIZ_SOFTDESK = os.getenv('URL_RAIZ_SOFTDESK')
API_KEY_SOFTDESK = os.getenv('API_KEY_SOFTDESK')
URL_API_OBTER_CHAMADO = '/api/api.php/chamado?codigo='

AMBIENTE = os.getenv('AMBIENTE')
ZABBIX_URL = os.getenv('ZABBIX_DEV_URL') if AMBIENTE == 'dev' else os.getenv('ZABBIX_PROD_URL')
ZABBIX_TOKEN = os.getenv('ZABBIX_DEV_TOKEN') if AMBIENTE == 'dev' else os.getenv('ZABBIX_PROD_TOKEN')

FILTRO_SEVERIDADE = int(args.severidade) if args.severidade else 1
DETERMINANTE = args.determinante if args.determinante else None
FILTRO_KEY = args.filtrokey if args.filtrokey else None
FILTRO_SLA = float(args.filtrosla) if args.filtrosla else None

# ------------------- FUNÇÕES AUX -------------------
def log_tempo_execucao(inicio, logger, mensagem='Tempo total de execução'):
    fim = dt.datetime.now()
    duracao = fim - inicio
    logger.info('%s: %s', mensagem, str(duracao))

def obterMes(args_mes, agora):
    if not args_mes:
        diaPrimeiro = agora.replace(day=1)
        mesPassado = diaPrimeiro - dt.timedelta(days=1)
        mes = mesPassado.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        mes = dt.datetime.strptime(f'{args_mes}-01 00:00:00', '%Y-%m-%d %H:%M:%S')

    return mes

def definirPeriodo(mes):
    mesSeguinte = mes.replace(day=28) + dt.timedelta(days=4)
    ultimoDoMes = mesSeguinte - dt.timedelta(days=mesSeguinte.day)
    timedateFim = ultimoDoMes.replace(hour=23, minute=59, second=59)

    epochInicio = mes.timestamp()
    epochFim = timedateFim.timestamp()

    periodo = {
        'inicio': int(epochInicio),
        'fim': int(epochFim)
    }

    return periodo

def fazerRequest(body, url):
    resposta = requests.post(url, headers={
        'Content-Type': 'application/json-rpc;charset=utf-8', 
        'Accept-Encoding': 'gzip',
        'User-Agent': 'cvsys-script',
    }, data=json.dumps(body), verify=False)

    if resposta.status_code != 200:
        logger.warning('Request falhou com status %s', resposta.status_code)
        return -1

    payload = resposta.json()
    return payload.get('result', -1)

def obterHosts(idGrupoSelecionado, token, url):
    logger.info('Obtendo hosts para grupo %s', idGrupoSelecionado)
    body = {
        'jsonrpc': '2.0', 'method': 'host.get',
        'params': {'groupids': idGrupoSelecionado,},
        'auth': token, 'id': 1
    }
    resposta = fazerRequest(body, url)
    if resposta == -1:
        sys.exit(1)
    logger.info('Foram encontrados %d hosts', len(resposta))

    return [{
        'hostid': h['hostid'],
        'hostname': h['host'],
        'nome_visivel': h['name'],
    } for h in resposta]

def timestampParaDataLegivel(ts):
    return dt.datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')

def obterIdsElementosSelecionados(lista, propriedade):
    return [elemento[propriedade] for elemento in lista]

def segmentaPeriodoParaRetry(periodo, fator):
    inicio, fim = periodo['inicio'], periodo['fim']
    passo = max(1, (fim - inicio) // fator)
    intervalos = []
    atual = inicio
    while atual < fim:
        subfim = min(atual + passo, fim)
        intervalos.append({'inicio': atual, 'fim': subfim})
        atual = subfim + 1
    return intervalos

def processaRepostaProblemas(resposta):
    problemasResultado = []

    reTicketSoftdesk = r'\b\d{5,6}\b'

    for item in resposta:
        dataLegivel = timestampParaDataLegivel(int(item['clock']))
        triggerid = item['relatedObject']['triggerid'] if item['relatedObject'] else None
        if len(item['acknowledges']) > 0:
            for i in item['acknowledges']:
                i['message'] = i['message'].replace('\n', ' ').replace('\r', ' ')

        match = re.findall(reTicketSoftdesk, str(item['acknowledges']))

        problemasResultado.append({
            'eventid': item['eventid'],
            'data': dataLegivel,
            'timestamp': item['clock'],
            'problema': item['name'],
            'severidade': item['severity'],
            'hostid': item['hosts'][0]['hostid'],
            'host': item['hosts'][0]['name'],
            'acknowledged': item['acknowledged'],
            **({'ack_msg_completa': item['acknowledges']} if item['acknowledges'] else {}),
            **({'ack_msg': match} if match else {}),
            'id_evento_recovery': item['r_eventid'],
            'triggerid': triggerid,
        })

    return problemasResultado

def obterProblemas(periodo, token, url, hosts=None, objects=None, fatorInicial=4):
    if hosts is None:
        hosts = []
    if objects is None:
        objects = []
    fator = fatorInicial
    while True:
        intervalos = segmentaPeriodoParaRetry(periodo, fator)
        problemasResultado = []
        erro = False
        for intervalo in intervalos:
            logger.info('Consultando eventos de %s até %s (fator=%d)', intervalo['inicio'], intervalo['fim'], fator)
            body = {
                'jsonrpc': '2.0',
                'method': 'event.get',
                'params': {
                    'output': 'extend',
                    'select_acknowledges': ['message'],
                    **({'hostids': hosts} if len(hosts) > 0 else {}),
                    **({'objectids': objects} if len(objects) > 0 else {}),
                    'selectHosts': ['hostid', 'name'],
                    'selectRelatedObject': 'extend',
                    'sortfield': ['clock', 'eventid'],
                    'sortorder': 'ASC',
                    'time_from': intervalo['inicio'],
                    'time_till': intervalo['fim'],
                },
                'auth': token,
                'id': 1
            }
            resposta = fazerRequest(body, url)
            if resposta == -1:
                erro = True
                break
            problemasResultado += processaRepostaProblemas(resposta)
        if not erro:
            logger.info('Total de %d problemas obtidos', len(problemasResultado))
            return problemasResultado
        fator *= 2
        if fator > 64:
            raise RuntimeError('Falha ao obter problemas: segmentação excessiva.')

def filtraProblemasPorSev(problemas, severidade):
    logger.info(f'Filtrando problemas por severidade {severidade}.')
    problemasFiltrados = []
    for item in problemas:
        if int(item['severidade']) >= severidade:
            problemasFiltrados.append(item)
    return problemasFiltrados

def filtraProblemasPorAck(problemas):
    logger.info('Filtrando problemas por acknowledge.')
    problemasFiltrados = []
    for item in problemas:
        if int(item['acknowledged']) == 1:
            problemasFiltrados.append(item)
    return problemasFiltrados

def correlacionarProblemas(problemasFiltrados, problemas):
    logger.info(f'Correlacionando {len(problemasFiltrados)} problemas com seus respectivos eventos de fechamento.')

    problemas_dict = {p['eventid']: p for p in problemas}
    problemasCorrelacionados = []

    for problema in problemasFiltrados:
        idResolucao = problema['id_evento_recovery']

        if idResolucao != '0':
            eventoResolucao = problemas_dict.get(idResolucao)

            if eventoResolucao:
                dataResolucao = eventoResolucao['timestamp']
                dataInicio = problema['timestamp']
                duracao_segundos = int(dataResolucao) - int(dataInicio)

                problema['resolvido_em'] = eventoResolucao['data']
                problema['duracao'] = str(dt.timedelta(seconds=duracao_segundos))
                problema['duracao_segundos'] = duracao_segundos
            else:
                problema['resolvido_em'] = 'N/E'
                problema['duracao'] = 0
                problema['duracao_segundos'] = 0
        else:
            problema['resolvido_em'] = 'N/R'
            problema['duracao'] = 0
            problema['duracao_segundos'] = 0

        problemasCorrelacionados.append(problema)

    return problemasCorrelacionados

def separaChamadosPorAck(eventos):
    logger.info('Separando eventos com mais de um número de chamado.')
    eventosMod = copy.deepcopy(eventos)
    eventosRetorno = []

    for evento in eventosMod:
        if 'ack_msg' not in evento:
            evento['ack_msg'] = 'N/A'
        elif len(evento['ack_msg']) > 1:
            for chamado in evento['ack_msg']:
                novaLinha = copy.deepcopy(evento)
                novaLinha['ack_msg'] = chamado
                eventosRetorno.append(novaLinha)
        elif len(evento['ack_msg']) == 1:
            evento['ack_msg'] = evento['ack_msg'][0]
            eventosRetorno.append(evento)
        else:
            evento['ack_msg'] = 'N/E'

    return eventosRetorno

def removeChamadosRepetidos(eventos):
    logger.info('Removendo eventos com mesmo ID e número de chamado.')
    eventosMod = copy.deepcopy(eventos)
    eventosRetorno = []
    vistos = set()

    for evento in eventosMod:
        chave = (evento['ack_msg'], evento['eventid'])
        if chave not in vistos:
            vistos.add(chave)
            eventosRetorno.append(evento)

    return eventosRetorno

def obterChamadosDedup(problemasConcatenadosComSla):
    logger.info('Obtendo IDs de chamados únicos.')
    chamadosDedup = list({e['ack_msg'] for e in problemasConcatenadosComSla if str(e.get('ack_msg')).isdigit()})

    logger.info(f'{len(chamadosDedup)} chamados únicos encontrados.')

    return chamadosDedup

def obterConteudoChamados(chamados, token, url, endpoint):
    logger.info('Iniciando consulta de chamados no Softdesk.')
    REQUEST_HEADERS = { 'hash_api': token }
    respostas = []
    logger.info(f'Consultando {len(chamados)} chamados no total.')
    for id in chamados:
        logger.info('Consultando chamado %s', id)
        time.sleep(1)
        resposta = requests.get(f'{url}{endpoint}{id}', headers=REQUEST_HEADERS)
        payload = resposta.json()
        if 'objeto' in payload:
            respostas.append(payload)
    return respostas

def processaChamados(chamados):
    logger.info('Processando chamados consultados.')
    chamadosProcessados = []

    for chamado in chamados:
        objeto = chamado['objeto']
        arrayCampos = objeto['campos_costumizaveis']
        campo_notaFechamento = [c['descricao'] for c in arrayCampos if c['campo_customizavel']['codigo'] == 5]
        notaFechamento = campo_notaFechamento[0] if len(campo_notaFechamento) > 0 else 'N/A'
        campo_causaRaiz = [c['descricao'] for c in arrayCampos if c['campo_customizavel']['codigo'] == 6]
        causaRaiz = campo_causaRaiz[0] if len(campo_causaRaiz) > 0 else 'N/A'
        campo_protocolo_operadora = [c['descricao'] for c in arrayCampos if c['campo_customizavel']['codigo'] == 7]
        protocoloOperadora = campo_protocolo_operadora[0] if len(campo_protocolo_operadora) > 0 else 'N/A'

        processado = {
            'id_chamado': objeto['codigo'],
            'id_cliente': objeto['cliente']['codigo'],
            'nome_cliente': objeto['cliente']['nome'],
            'atendente': objeto['atendente']['nome'],
            'prioridade': objeto['prioridade']['descricao'],
            'status': objeto['status']['descricao'],
            'titulo': objeto['titulo'],
            'abertura': f'{objeto['data_abertura']}T{objeto['hora_abertura']}',
            **({'encerramento': f'{objeto['data_encerramento']}T{objeto['hora_encerramento']}'} if objeto['data_encerramento'] else {}),
            'nota_fechamento': notaFechamento,
            'causa_raiz': causaRaiz,
            'protocolo_operadora': protocoloOperadora,
        }

        chamadosProcessados.append(processado)

    return chamadosProcessados

def filtraSlaPorDeterminante(slaPorTrigger, determinante):
    logger.info(f'Filtrando SLA por determinante selecionado: "{determinante}"')
    slaFiltrado = []

    for trigger in slaPorTrigger:
        if trigger['key'] == determinante:
            slaFiltrado.append(trigger)

    slaFiltradoOrdenado = sorted(
        slaFiltrado,
        key=lambda x: float(x['sla'])
    )

    return slaFiltradoOrdenado

def calculaSlaPorTrigger(triggers, hosts, problemas, periodo):
    logger.info('Calculando SLA por trigger.')
    slaCalculado = []
    mesEmSegundos = periodo['fim'] - periodo['inicio']

    agregado = defaultdict(lambda: {'hostid': '', 'problema': '', 'severidade': '', 'soma_duracao': 0})

    for problema in problemas:
        triggerid = problema['triggerid']
        agregado[triggerid]['hostid'] = problema['hostid']
        agregado[triggerid]['problema'] = problema['problema']
        agregado[triggerid]['severidade'] = problema['severidade']
        agregado[triggerid]['soma_duracao'] += problema['duracao_segundos']

    for triggerid, values in agregado.items():
        lambdaItens = list(filter(lambda hosts: hosts['hostid'] == values['hostid'], hosts))[0]
        nomeHost, idHost = lambdaItens['hostname'], lambdaItens['hostid']
        trigger_key = [t['items'][0]['key_'] for t in triggers if triggerid == t['triggerid']][0]

        segundosTotais = values['soma_duracao']
        horas = segundosTotais // 3600
        minutos = (segundosTotais % 3600) // 60
        segundos = segundosTotais % 60
        duracaoFormatada = f"{int(horas):02}:{int(minutos):02}:{int(segundos):02}"

        porcentagemSla = 100 - (values['soma_duracao'] / mesEmSegundos * 100.0)

        slaCalculado.append({
            'hostid': idHost,
            'host': nomeHost,
            'triggerid': triggerid,
            'key': trigger_key,
            'problema': values['problema'],
            'severidade': values['severidade'],
            'soma_duracao_segundos': values['soma_duracao'],
            'soma_duracao': duracaoFormatada,
            'sla': float(round(porcentagemSla, 2))
        })

    slaCalculadoOrdenado = sorted(
        slaCalculado,
        key=lambda x: str(x['host'])
    )

    return slaCalculadoOrdenado

def segmentaArrayPorFator(array, fator):
    k, m = divmod(len(array), fator)
    return [array[i*k + min(i, m):(i+1)*k + min(i+1, m)] for i in range(fator)]

def obterItens(hosts, filtro_key, token, url, fatorInicial=1):
    fator = fatorInicial

    while True:
        logger.info(f'Fator para consulta de itens: {fator}')
        intervaloHosts = segmentaArrayPorFator(hosts, fator)
        itensResultado = []
        erro = False

        for intervalo in intervaloHosts:
            logger.info(f'Consultando {len(intervalo)} hosts: de {intervalo[0]} até {intervalo[-1]}')
            if not filtro_key:
                body = {
                    'jsonrpc': '2.0',
                    'method': 'item.get',
                    'params': {
                        'output': ['itemid', 'hostid', 'name', 'key_', 'units', 'description', 'lastclock', 'lastns', 'lastvalue', 'prevvalue'],
                        'hostids': intervalo,
                        'selectHosts': ['name'],
                        'sortfield': 'name',
                        'selectTriggers': ['triggerid', 'description']
                    },
                    'auth': token,
                    'id': 1
                }

                resposta = fazerRequest(body, url)

                if resposta == -1:
                    erro = True
                    break
                for item in resposta:
                    itensResultado.append(item)

            else:
                for filtro in filtro_key:
                    body = {
                        'jsonrpc': '2.0',
                        'method': 'item.get',
                        'params': {
                            'output': ['itemid', 'hostid', 'name', 'key_', 'units', 'description', 'lastclock', 'lastns', 'lastvalue', 'prevvalue'],
                            'hostids': intervalo,
                            'search': {
                                'key_': str(filtro),
                            },
                            'searchWildcardsEnabled': True,
                            'selectHosts': ['name'],
                            'sortfield': 'name',
                            'selectTriggers': ['triggerid', 'description']
                        },
                        'auth': token,
                        'id': 1
                    }

                    resposta = fazerRequest(body, url)

                    if resposta == -1:
                        erro = True
                        break
                    for item in resposta:
                        itensResultado.append(item)

        if not erro:
            logger.info('Total de %d itens obtidos', len(itensResultado))
            return itensResultado
        fator *= 2
        if fator > 64:
            raise RuntimeError('Falha ao obter itens: segmentação excessiva.')

def obterTriggers(itens, token, url, fatorInicial=1):
    fator = fatorInicial
    while True:
        logger.info(f'Fator para consulta de triggers: {fator}')
        intervaloItens = segmentaArrayPorFator(itens, fator)
        triggersResultado = []
        erro = False

        for intervalo in intervaloItens:
            logger.info(f'Consultando {len(intervalo)} itens: de {intervalo[0]} até {intervalo[-1]}')

            body = {
                'jsonrpc': '2.0',
                'method': 'trigger.get',
                'params': {
                    'itemids': intervalo,
                    'output': ['triggerid', 'expression', 'description', 'status', 'priority', 'lastchange', 'comments', 'state'],
                    'selectHosts': ['hostid', 'host', 'name'],
                    'selectItems': ['itemid', 'hostid', 'name', 'key_'],
                    'min_severity': FILTRO_SEVERIDADE
                },
                'auth': token,
                'id': 1
            }

            resposta = fazerRequest(body, url)

            if resposta == -1:
                erro = True
                break
            for item in resposta:
                triggersResultado.append(item)

        if not erro:
            logger.info('Total de %d triggers obtidos', len(triggersResultado))
            return triggersResultado
        fator *= 2
        if fator > 64:
            raise RuntimeError('Falha ao obter triggers: segmentação excessiva.')

def concatenaComSla(problemasUnicos, slaPorTrigger):
    logger.info('Concatenando eventos com SLA calculado.')
    problemasConcatenadosComSla = []

    for problema in problemasUnicos:
        problema['sla'] = [sla['sla'] for sla in slaPorTrigger if sla['triggerid'] == problema['triggerid']][0]
        problemasConcatenadosComSla.append(problema)

    logger.info(f'{len(problemasConcatenadosComSla)} chamados concatenados.')

    return problemasConcatenadosComSla

def filtraProblemasPorSla(problemasConcatenadosComSla, filtro_sla):
    logger.info(f'Filtrando problemas com filtro {filtro_sla}')

    problemasFiltradosPorSla = [p for p in problemasConcatenadosComSla if float(p['sla']) < float(filtro_sla)]

    logger.info(f'{len(problemasFiltradosPorSla)} chamados filtrados por SLA.')

    return problemasFiltradosPorSla

def filtraProblemasPorDeterminante(problemasConcatenadosComSla, slaPorTrigger, determinante):
    trigger_para_key = {sla['triggerid']: sla['key'] for sla in slaPorTrigger}
    
    problemasFiltrados = []
    for p in problemasConcatenadosComSla:
        key = trigger_para_key.get(p['triggerid'])
        if key == determinante:
            problemasFiltrados.append(p)
    return problemasFiltrados

def renderizaSaidaPorHost(problemasUnicos, conteudoChamados, FILTRO_SLA, slaPorDeterminante):
    logger.info('Iniciando render por host.')
    saida = []

    for sla_info in slaPorDeterminante:
        hostid = sla_info['hostid']
        hostname = sla_info['host']
        sla = sla_info['sla']
        duracao = sla_info['soma_duracao']

        if sla < FILTRO_SLA or FILTRO_SLA == None:
            saida.append(f'## {hostname}\n')
            saida.append(f'**SLA do host neste período**: {str(round(sla, 2)).replace('.',',')}%\n')
            saida.append(f'**Tempo total de indisponibilidade**: {duracao}\n\n')

            vistos = set()
            for ev in [e for e in problemasUnicos if e['hostid'] == hostid]:
                ack = ev.get('ack_msg')
                if not ack or not str(ack).isdigit():
                    continue
                if ack not in vistos:
                    vistos.add(ack)
                    chamado = next((c for c in conteudoChamados if str(c['id_chamado']) == str(ack)), None)
                    if chamado:
                        saida.append(f'### Chamado {chamado["id_chamado"]}\n')
                        saida.append(f'> Nota de fechamento: {chamado["nota_fechamento"]}\n> Causa raiz: {chamado["causa_raiz"]}\n')
                        df = pd.DataFrame(
                            [x for x in problemasUnicos if x['ack_msg'] == ack and x['hostid'] == hostid],
                            columns=['data','problema','severidade','duracao','sla']
                        )
                        saida.append(
                            f'{df.rename(columns={'data':'Data',
                                                  'problema':'Incidente',
                                                  'severidade':'Severidade',
                                                  'duracao':'Duração',
                                                  'sla': 'SLA do item'}).to_html(index=False)}\n'
                        )

    return saida

def renderizaSaidaPorTrigger(problemasUnicos, conteudoChamados, FILTRO_SLA, slaPorTrigger):
    if FILTRO_SLA == None:
        FILTRO_SLA = 100
    logger.info('Iniciando render por trigger.')
    saida = []
    hostsVistos = set()

    for sla_info in slaPorTrigger:
        hostid = sla_info['hostid']
        hostname = sla_info['host']

        if hostid not in hostsVistos:
            hostsVistos.add(hostid)
        else:
            continue

        if len([e for e in problemasUnicos if e['hostid'] == hostid and e['sla'] < FILTRO_SLA]) > 0:
            saida.append(f'## {hostname}\n')
        else:
            continue

        vistos = set()

        for ev in [e for e in problemasUnicos if e['hostid'] == hostid and e['sla'] < FILTRO_SLA]:
            ack = ev.get('ack_msg')
            if not ack or not str(ack).isdigit():
                continue
            if ack not in vistos:
                vistos.add(ack)
                chamado = next((c for c in conteudoChamados if str(c['id_chamado']) == str(ack)), None)
                if chamado:
                    saida.append(f'### Chamado {chamado["id_chamado"]}\n')
                    saida.append(f'> Nota de fechamento: {chamado["nota_fechamento"]}\n> Causa raiz: {chamado["causa_raiz"]}\n')
                    df = pd.DataFrame(
                        [x for x in problemasUnicos if x['ack_msg'] == ack and x['hostid'] == hostid],
                        columns=['data','problema','severidade','duracao','sla']
                    )
                    saida.append(
                        f'{df.rename(columns={'data':'Data',
                                              'problema':'Incidente',
                                              'host':'Hostname',
                                              'triggerid':'ID alarme',
                                              'severidade':'Severidade',
                                              'duracao':'Duração',
                                              'sla': 'SLA do item'}).to_html(index=False)}\n'
                    )

    return saida

def main():
    mes = obterMes(args.mes, AGORA)
    periodo = definirPeriodo(mes)

    hosts = obterHosts(args.groupids, ZABBIX_TOKEN, ZABBIX_URL)
    arrayIdsHostsSelecionados = obterIdsElementosSelecionados(hosts, 'hostid')

    if DETERMINANTE and FILTRO_KEY:
        FILTRO_KEY.append(DETERMINANTE)

    itens = obterItens(arrayIdsHostsSelecionados, FILTRO_KEY, ZABBIX_TOKEN, ZABBIX_URL)
    arrayIdsItensSelecionados = obterIdsElementosSelecionados(itens, 'itemid')

    triggers = obterTriggers(arrayIdsItensSelecionados, ZABBIX_TOKEN, ZABBIX_URL)
    arrayIdsTriggersSelecionados = obterIdsElementosSelecionados(triggers, 'triggerid')

    problemas = obterProblemas(periodo, ZABBIX_TOKEN, ZABBIX_URL, objects=arrayIdsTriggersSelecionados)

    problemasFiltradosSev= filtraProblemasPorSev(problemas, FILTRO_SEVERIDADE)
    problemasCorrelacionados = correlacionarProblemas(problemasFiltradosSev, problemas)

    problemasAck = filtraProblemasPorAck(problemasCorrelacionados)
    problemasUnicos = removeChamadosRepetidos(separaChamadosPorAck(problemasAck))

    slaPorTrigger = calculaSlaPorTrigger(triggers, hosts, problemasCorrelacionados, periodo)

    problemasConcatenadosComSla = concatenaComSla(problemasUnicos, slaPorTrigger)

    if FILTRO_SLA:
        problemasConcatenadosComSla = filtraProblemasPorSla(problemasConcatenadosComSla, FILTRO_SLA)

    if DETERMINANTE:
        slaPorDeterminante = filtraSlaPorDeterminante(slaPorTrigger, DETERMINANTE)
        problemasConcatenadosComSla = filtraProblemasPorDeterminante(
            problemasConcatenadosComSla,
            slaPorTrigger,
            DETERMINANTE
        )

    chamadosDedup = obterChamadosDedup(problemasConcatenadosComSla)

    conteudoChamados = processaChamados(
        obterConteudoChamados(
            chamadosDedup,
            API_KEY_SOFTDESK,
            URL_RAIZ_SOFTDESK,
            URL_API_OBTER_CHAMADO
        )
    )

    if DETERMINANTE:
        saidaRenderizada = renderizaSaidaPorHost(problemasUnicos, conteudoChamados, FILTRO_SLA, slaPorDeterminante)
    else:
        saidaRenderizada = renderizaSaidaPorTrigger(problemasUnicos, conteudoChamados, FILTRO_SLA, slaPorTrigger)

    with open(args.saida, 'w', encoding='utf-8') as f:
        f.write('\n'.join(saidaRenderizada))
    logger.info('Relatório salvo em %s', args.saida)

    log_tempo_execucao(AGORA, logger)

if __name__ == '__main__':
    main()

