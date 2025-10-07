import sqlite3
from datetime import datetime

def view_database():
    """View all data in the database with nice formatting"""
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        print("="*50)
        print("📊 DATABASE VIEWER")
        print("="*50)
        print(f"⏰ Viewed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Users table
        print("👥 USERS TABLE:")
        print("-" * 40)
        c.execute("SELECT * FROM users")
        users = c.fetchall()
        if users:
            print("User ID    | Username      | Leader ID | Role Given | Joined At")
            print("-" * 65)
            for user in users:
                print(f"{user[0]:<10} | {user[1]:<12} | {user[2]:<9} | {user[3]:<10} | {user[4]}")
        else:
            print("No users found.")
        print()
        
        # Leaders table
        print("👑 LEADERS TABLE:")
        print("-" * 40)
        c.execute("SELECT * FROM leaders")
        leaders = c.fetchall()
        if leaders:
            print("ID | Name       | Commission | Balance")
            print("-" * 35)
            for leader in leaders:
                print(f"{leader[0]:<2} | {leader[1]:<10} | {leader[2]*100:>8.1f}% | {leader[3]:>7}")
        else:
            print("No leaders found.")
        print()
        
        # Payments table
        print("💳 PAYMENTS TABLE:")
        print("-" * 40)
        c.execute("SELECT * FROM payments")
        payments = c.fetchall()
        if payments:
            print("Payment ID | User ID | Amount | Status  | Leader | Created At")
            print("-" * 60)
            for payment in payments:
                print(f"{payment[0]:<10} | {payment[1]:<7} | {payment[2]:>6} | {payment[3]:<7} | {payment[4]:<6} | {payment[5]}")
        else:
            print("No payments found.")
        print()
        
        # Summary
        print("📈 SUMMARY:")
        print("-" * 20)
        print(f"Total Users: {len(users)}")
        print(f"Total Leaders: {len(leaders)}")
        print(f"Total Payments: {len(payments)}")
        if payments:
            total_amount = sum(payment[2] for payment in payments)
            print(f"Total Payment Amount: {total_amount:,} MNT")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error viewing database: {e}")

if __name__ == "__main__":
    view_database()