import argparse
from app import create_app
from app.models import Client
import requests
import time


def test_softdesk(client_id, tickets):
    app = create_app()
    with app.app_context():
        client = Client.query.get(client_id)
        if not client:
            print(f"Cliente id={client_id} nao encontrado.")
            return
        if not getattr(client, 'softdesk_enabled', False):
            print(f"Cliente {client.name} nao tem Softdesk habilitado.")
            return
        base_url = getattr(client, 'softdesk_base_url', None)
        api_key = getattr(client, 'softdesk_api_key', None)
        if not base_url or not api_key:
            print("Credenciais Softdesk ausentes.")
            return
        headers = {'hash_api': api_key}
        base = base_url.rstrip('/')
        for idx, tid in enumerate(tickets):
            url = f"{base}/api/api.php/chamado?codigo={tid}"
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                print(f"Ticket {tid}: status {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and 'objeto' in data:
                        obj = data['objeto']
                        print(f"  titulo={obj.get('titulo')} status={obj.get('status', {}).get('descricao')}")
                    else:
                        print("  resposta inesperada:", data)
                else:
                    print("  body:", resp.text[:200])
            except requests.RequestException as exc:
                print(f"  erro: {exc}")
            if idx < len(tickets) - 1:
                time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description='Testa conexao com Softdesk para um cliente.')
    parser.add_argument('--client', type=int, required=True, help='ID do cliente')
    parser.add_argument('--tickets', nargs='+', required=True, help='IDs de chamado para testar')
    args = parser.parse_args()
    test_softdesk(args.client, args.tickets)


if __name__ == '__main__':
    main()
