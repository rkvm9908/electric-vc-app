from app import app
from models import db, User, Station, Branch, Slot
from datetime import time

def seed():
    with app.app_context():
        # Drop and create tables
        db.drop_all()
        db.create_all()

        # Create Admin
        admin = User(username='admin', email='admin@evcharge.com', vehicle_no='ADMIN-01', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)

        # Create Sample User
        user = User(username='johndoe', email='user@evcharge.com', vehicle_no='TN-01-AB-1234', role='user', bio='Loving the eco-friendly life! 🌿')
        user.set_password('user123')
        db.session.add(user)

        # Create Stations in Tamil Nadu
        stations = [
            {'name': 'Chennai Central Hub', 'location': 'Chennai, TN', '2w': 10, '4w': 5, 'lat': 13.0827, 'lng': 80.2707, 'price_2w': 20.0, 'price_4w': 50.0},
            {'name': 'Coimbatore Ecocharge', 'location': 'Coimbatore, TN', '2w': 8, '4w': 4, 'lat': 11.0168, 'lng': 76.9558, 'price_2w': 18.0, 'price_4w': 45.0},
            {'name': 'Madurai Power Point', 'location': 'Madurai, TN', '2w': 6, '4w': 3, 'lat': 9.9252, 'lng': 78.1198, 'price_2w': 22.0, 'price_4w': 55.0},
            {'name': 'Salem FastCharge', 'location': 'Salem, TN', '2w': 5, '4w': 2, 'lat': 11.6643, 'lng': 78.1460, 'price_2w': 19.0, 'price_4w': 48.0},
        ]

        for s_data in stations:
            station = Station(
                name=s_data['name'],
                location=s_data['location'],
                latitude=s_data['lat'],
                longitude=s_data['lng']
            )
            db.session.add(station)
            db.session.flush()

            branch = Branch(
                station_id=station.id,
                name=f"{station.name} Main Branch",
                location=station.location,
                latitude=station.latitude,
                longitude=station.longitude,
                slots_2w_total=s_data['2w'],
                slots_4w_total=s_data['4w'],
                price_2w_per_hour=s_data['price_2w'],
                price_4w_per_hour=s_data['price_4w'],
                open_time=time(6, 0),
                close_time=time(22, 0)
            )
            db.session.add(branch)
            db.session.flush()

            for index in range(1, s_data['2w'] + 1):
                db.session.add(Slot(
                    station_id=station.id,
                    branch_id=branch.id,
                    type='2W',
                    status='Available',
                    _branch_name=f"{branch.branch_code}-2W-{index:02d}"
                ))
            for index in range(1, s_data['4w'] + 1):
                db.session.add(Slot(
                    station_id=station.id,
                    branch_id=branch.id,
                    type='4W',
                    status='Available',
                    _branch_name=f"{branch.branch_code}-4W-{index:02d}"
                ))

        db.session.commit()
        print("Database seeded successfully!")

if __name__ == "__main__":
    seed()
