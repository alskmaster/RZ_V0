from app import create_app, db
from app.models import Client

def main():
    app = create_app()
    with app.app_context():
        clients = Client.query.order_by(Client.id).all()
        if not clients:
            print('No clients found in DB')
            return
        for c in clients:
            print(f"ID={c.id} | name={c.name}")

if __name__ == '__main__':
    main()

