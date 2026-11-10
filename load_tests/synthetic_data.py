from app.models.models import User, Client, Case
from app.config.constants import USER_ROLES, letters,chars,ALLOWED_CASE_TYPES
from app.extensions.extensions import bcrypt
from datetime import date, timedelta
import random

def generate_synthetic_clients(count=4):
        clients= []
        dob = 0        
        test_date1, test_date2 = date(1960, 1, 1), date(2005, 12, 31)        
        dates_bet = test_date2 - test_date1
        total_days = dates_bet.days 
        rng = random.Random(42) 
    
        for i in range(1, count + 1):
                
                        
            randay = rng.randint(0, total_days)
            dob = test_date1 + timedelta(days=randay)

            clients.append(
                Client(client_first_name=f"Test_client_first_name{i}",
                       client_lastname=f"Test_client_last_name{i}",
                       client_phone=f"000{i:07d}",
                       client_email=f"Test_client_email{i}@test.test",
                       client_address=f"Test_client_address{i}",
                       client_date_of_birth=dob
                      )
                 )
        return clients

def generate_synthetic_users(count=4):
        users= []
        random_mix = letters + "".join(chars)
        for i in range(1,count + 1):
            password = [random.choice(random_mix) for _ in range(9)]
            hashed_password = bcrypt.generate_password_hash("".join(password)).decode("utf-8")
            users.append(
                User(user_name=f"test_user{i}",
                     user_email=f"test_user{i}@test.test",
                     user_role=USER_ROLES["STAFF"],
                     user_password=hashed_password,
                     is_active=True,
                        )
                      )
                 
        return users

def generate_synthetic_cases(clients, users, count= 5):
        cases= []        
        rng = random.Random(43)

        for i in range(count):          
           
            case = Case(case_type = rng.choice(ALLOWED_CASE_TYPES),
                     case_status= 'open',
                     case_stage='intake',
                     client= rng.choice(clients),                    
                     assigned_users = [rng.choice(users)]
                      )
                 
            cases.append(case)
        return cases