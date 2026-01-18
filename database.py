import os
from contextlib import contextmanager
from datetime import datetime, timedelta

from config import DATABASE_URL

try:
    import psycopg2
    from psycopg2.pool import SimpleConnectionPool
    PSYCOPG2_AVAILABLE = True
    CONNECTION_POOL = None
except ImportError:
    PSYCOPG2_AVAILABLE = False
    CONNECTION_POOL = None

class FakeDatabase:
    def __init__(self):
        self.global_stats = {
            'total_shleps': 0, 
            'last_shlep': None,
            'max_damage': 0,
            'max_damage_user_id': None,
            'max_damage_username': None,
            'max_damage_date': None
        }
        self.user_stats = {}
        self.chat_stats = {}
        self.chat_votes = {}
        self.chat_duels = {}
        self.chat_roles = {}
    
    def add_shlep(self, user_id: int, username: str, damage: int = 0, chat_id: int = None):
        now = datetime.now()
        self.global_stats['total_shleps'] += 1
        self.global_stats['last_shlep'] = now
        
        if damage > self.global_stats['max_damage']:
            self.global_stats['max_damage'] = damage
            self.global_stats['max_damage_user_id'] = user_id
            self.global_stats['max_damage_username'] = username
            self.global_stats['max_damage_date'] = now
        
        if user_id not in self.user_stats:
            self.user_stats[user_id] = {'username': username, 'shlep_count': 0, 'last_shlep': None}
        
        self.user_stats[user_id]['shlep_count'] += 1
        self.user_stats[user_id]['last_shlep'] = now
        self.user_stats[user_id]['username'] = username
        
        if chat_id:
            if chat_id not in self.chat_stats:
                self.chat_stats[chat_id] = {
                    'total_shleps': 0,
                    'users': {},
                    'max_damage': 0,
                    'max_damage_user_id': None,
                    'max_damage_username': None,
                    'max_damage_date': None
                }
            
            self.chat_stats[chat_id]['total_shleps'] += 1
            
            if user_id not in self.chat_stats[chat_id]['users']:
                self.chat_stats[chat_id]['users'][user_id] = {
                    'username': username,
                    'shlep_count': 0,
                    'last_shlep': None
                }
            
            self.chat_stats[chat_id]['users'][user_id]['shlep_count'] += 1
            self.chat_stats[chat_id]['users'][user_id]['last_shlep'] = now
            
            if damage > self.chat_stats[chat_id]['max_damage']:
                self.chat_stats[chat_id]['max_damage'] = damage
                self.chat_stats[chat_id]['max_damage_user_id'] = user_id
                self.chat_stats[chat_id]['max_damage_username'] = username
                self.chat_stats[chat_id]['max_damage_date'] = now
        
        return self.global_stats['total_shleps'], self.user_stats[user_id]['shlep_count'], self.global_stats['max_damage']

fake_db = FakeDatabase()

def init_connection_pool():
    global CONNECTION_POOL
    if PSYCOPG2_AVAILABLE and DATABASE_URL:
        try:
            CONNECTION_POOL = SimpleConnectionPool(
                1, 10,
                dsn=DATABASE_URL
            )
        except Exception as e:
            CONNECTION_POOL = None

@contextmanager
def get_connection():
    if not PSYCOPG2_AVAILABLE or not DATABASE_URL:
        class StubConnection:
            def cursor(self): 
                return StubCursor()
            def commit(self): 
                pass
            def close(self): 
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        
        class StubCursor:
            def __init__(self):
                self.result = None
            
            def execute(self, query, params=None):
                query_lower = query.lower().strip()
                
                if "insert into global_stats" in query_lower:
                    fake_db.global_stats = {
                        'total_shleps': 0, 
                        'last_shlep': None,
                        'max_damage': 0,
                        'max_damage_user_id': None,
                        'max_damage_username': None,
                        'max_damage_date': None
                    }
                elif "update global_stats" in query_lower and "returning total_shleps" in query_lower:
                    fake_db.global_stats['last_shlep'] = params[0] if params else datetime.now()
                    self.result = [(fake_db.global_stats['total_shleps'],)]
                elif "select total_shleps, last_shlep, max_damage, max_damage_username, max_damage_date from global_stats" in query_lower:
                    stats = fake_db.global_stats
                    self.result = [(
                        stats['total_shleps'], 
                        stats['last_shlep'],
                        stats['max_damage'],
                        stats['max_damage_username'],
                        stats['max_damage_date']
                    )]
                elif "insert into user_stats" in query_lower or "update user_stats" in query_lower:
                    if "returning shlep_count" in query_lower:
                        user_id = params[0]
                        self.result = [(fake_db.user_stats.get(user_id, {}).get('shlep_count', 1),)]
                elif "select username, shlep_count from user_stats" in query_lower:
                    users = []
                    for uid, data in fake_db.user_stats.items():
                        users.append((data['username'], data['shlep_count']))
                    users.sort(key=lambda x: x[1], reverse=True)
                    limit = params[0] if params else 10
                    self.result = users[:limit]
                elif "select username, shlep_count, last_shlep from user_stats" in query_lower:
                    user_id = params[0]
                    data = fake_db.user_stats.get(user_id)
                    if data:
                        self.result = [(data['username'], data['shlep_count'], data['last_shlep'])]
                    else:
                        self.result = [(f"Игрок_{user_id}", 0, None)]
                elif "insert into chat_stats" in query_lower or "select from chat_stats" in query_lower:
                    if params and len(params) > 0:
                        chat_id = params[0]
                        if chat_id in fake_db.chat_stats:
                            stats = fake_db.chat_stats[chat_id]
                            users_list = [(data['username'], data['shlep_count']) for data in stats['users'].values()]
                            users_list.sort(key=lambda x: x[1], reverse=True)
                            self.result = users_list[:10]
                        else:
                            self.result = []
                
                return self
            
            def fetchone(self):
                if self.result and len(self.result) > 0:
                    return self.result[0]
                return None
            
            def fetchall(self):
                return self.result or []
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass
        
        yield StubConnection()
        return
    
    try:
        if CONNECTION_POOL:
            conn = CONNECTION_POOL.getconn()
            try:
                yield conn
            finally:
                CONNECTION_POOL.putconn(conn)
        else:
            conn = psycopg2.connect(DATABASE_URL)
            try:
                yield conn
            finally:
                conn.close()
    except Exception as e:
        yield None

def init_db():
    init_connection_pool()
    
    with get_connection() as conn:
        if conn is None:
            return
        
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS global_stats (
                    id SERIAL PRIMARY KEY,
                    total_shleps BIGINT DEFAULT 0,
                    last_shlep TIMESTAMP,
                    max_damage INT DEFAULT 0,
                    max_damage_user_id BIGINT,
                    max_damage_username VARCHAR(100),
                    max_damage_date TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id BIGINT PRIMARY KEY,
                    username VARCHAR(100),
                    shlep_count INT DEFAULT 0,
                    last_shlep TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_stats (
                    chat_id BIGINT PRIMARY KEY,
                    total_shleps BIGINT DEFAULT 0,
                    max_damage INT DEFAULT 0,
                    max_damage_user_id BIGINT,
                    max_damage_username VARCHAR(100),
                    max_damage_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_user_stats (
                    chat_id BIGINT,
                    user_id BIGINT,
                    username VARCHAR(100),
                    shlep_count INT DEFAULT 0,
                    last_shlep TIMESTAMP,
                    PRIMARY KEY (chat_id, user_id)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_votes (
                    vote_id SERIAL PRIMARY KEY,
                    chat_id BIGINT,
                    message_id BIGINT,
                    initiator_id BIGINT,
                    initiator_name VARCHAR(100),
                    question TEXT,
                    yes_votes INT DEFAULT 0,
                    no_votes INT DEFAULT 0,
                    voters JSONB DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ends_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_duels (
                    duel_id SERIAL PRIMARY KEY,
                    chat_id BIGINT,
                    challenger_id BIGINT,
                    challenger_name VARCHAR(100),
                    target_id BIGINT,
                    target_name VARCHAR(100),
                    challenger_score INT DEFAULT 0,
                    target_score INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ends_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    winner_id BIGINT
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_roles (
                    chat_id BIGINT,
                    user_id BIGINT,
                    role_type VARCHAR(50),
                    role_name VARCHAR(100),
                    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    PRIMARY KEY (chat_id, user_id, role_type)
                )
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_user_stats_shlep 
                ON chat_user_stats(chat_id, shlep_count DESC)
            """)
            
            cur.execute("SELECT COUNT(*) FROM global_stats")
            if cur.fetchone()[0] == 0:
                cur.execute("INSERT INTO global_stats (total_shleps) VALUES (0)")
            
            conn.commit()

def add_shlep(user_id: int, username: str, damage: int = 0, chat_id: int = None):
    if not DATABASE_URL:
        return fake_db.add_shlep(user_id, username, damage, chat_id)
    
    with get_connection() as conn:
        if conn is None:
            return (0, 0, 0)
        
        with conn.cursor() as cur:
            now = datetime.now()
            
            cur.execute("""
                UPDATE global_stats 
                SET total_shleps = total_shleps + 1, last_shlep = %s
                WHERE id = 1
                RETURNING total_shleps
            """, (now,))
            total = cur.fetchone()[0]
            
            cur.execute("""
                INSERT INTO user_stats (user_id, username, shlep_count, last_shlep)
                VALUES (%s, %s, 1, %s)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    shlep_count = user_stats.shlep_count + 1,
                    last_shlep = %s,
                    username = EXCLUDED.username
                RETURNING shlep_count
            """, (user_id, username, now, now))
            user_count = cur.fetchone()[0]
            
            cur.execute("SELECT max_damage FROM global_stats WHERE id = 1")
            current_max_damage = cur.fetchone()[0] or 0
            
            if damage > current_max_damage:
                cur.execute("""
                    UPDATE global_stats 
                    SET max_damage = %s,
                        max_damage_user_id = %s,
                        max_damage_username = %s,
                        max_damage_date = %s
                    WHERE id = 1
                """, (damage, user_id, username, now))
            
            if chat_id:
                cur.execute("""
                    INSERT INTO chat_stats (chat_id, total_shleps, last_activity)
                    VALUES (%s, 1, %s)
                    ON CONFLICT (chat_id) 
                    DO UPDATE SET 
                        total_shleps = chat_stats.total_shleps + 1,
                        last_activity = %s
                """, (chat_id, now, now))
                
                cur.execute("""
                    INSERT INTO chat_user_stats (chat_id, user_id, username, shlep_count, last_shlep)
                    VALUES (%s, %s, %s, 1, %s)
                    ON CONFLICT (chat_id, user_id) 
                    DO UPDATE SET 
                        shlep_count = chat_user_stats.shlep_count + 1,
                        last_shlep = %s,
                        username = EXCLUDED.username
                """, (chat_id, user_id, username, now, now))
                
                cur.execute("SELECT max_damage FROM chat_stats WHERE chat_id = %s", (chat_id,))
                chat_max_damage = cur.fetchone()
                chat_max_damage = chat_max_damage[0] if chat_max_damage else 0
                
                if damage > chat_max_damage:
                    cur.execute("""
                        UPDATE chat_stats 
                        SET max_damage = %s,
                            max_damage_user_id = %s,
                            max_damage_username = %s,
                            max_damage_date = %s
                        WHERE chat_id = %s
                    """, (damage, user_id, username, now, chat_id))
            
            conn.commit()
            return total, user_count, current_max_damage

def get_stats():
    if not DATABASE_URL:
        stats = fake_db.global_stats
        return (
            stats['total_shleps'], 
            stats['last_shlep'],
            stats['max_damage'],
            stats['max_damage_username'],
            stats['max_damage_date']
        )
    
    with get_connection() as conn:
        if conn is None:
            return (0, None, 0, None, None)
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    total_shleps, 
                    last_shlep,
                    max_damage,
                    max_damage_username,
                    max_damage_date
                FROM global_stats 
                WHERE id = 1
            """)
            result = cur.fetchone()
            return result if result else (0, None, 0, None, None)

def get_top_users(limit=10):
    if not DATABASE_URL:
        users = []
        for uid, data in fake_db.user_stats.items():
            users.append((data['username'], data['shlep_count']))
        users.sort(key=lambda x: x[1], reverse=True)
        return users[:limit]
    
    with get_connection() as conn:
        if conn is None:
            return []
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, shlep_count 
                FROM user_stats 
                ORDER BY shlep_count DESC 
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

def get_user_stats(user_id: int):
    if not DATABASE_URL:
        data = fake_db.user_stats.get(user_id)
        if data:
            return (data['username'], data['shlep_count'], data['last_shlep'])
        return (f"Игрок_{user_id}", 0, None)
    
    with get_connection() as conn:
        if conn is None:
            return (f"Игрок_{user_id}", 0, None)
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, shlep_count, last_shlep 
                FROM user_stats 
                WHERE user_id = %s
            """, (user_id,))
            result = cur.fetchone()
            if result:
                return result
            cur.execute("""
                INSERT INTO user_stats (user_id, username, shlep_count)
                VALUES (%s, %s, 0)
                ON CONFLICT (user_id) DO NOTHING
                RETURNING username, shlep_count, last_shlep
            """, (user_id, f"Игрок_{user_id}"))
            conn.commit()
            return (f"Игрок_{user_id}", 0, None)

def get_chat_stats(chat_id: int):
    if not DATABASE_URL:
        if chat_id in fake_db.chat_stats:
            stats = fake_db.chat_stats[chat_id]
            return {
                'total_shleps': stats['total_shleps'],
                'max_damage': stats['max_damage'],
                'max_damage_user': stats['max_damage_username'],
                'max_damage_date': stats['max_damage_date'],
                'total_users': len(stats['users']),
                'active_today': 0
            }
        return None
    
    with get_connection() as conn:
        if conn is None:
            return None
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    total_shleps,
                    max_damage,
                    max_damage_username,
                    max_damage_date,
                    last_activity
                FROM chat_stats 
                WHERE chat_id = %s
            """, (chat_id,))
            result = cur.fetchone()
            
            if result:
                total_shleps, max_damage, max_damage_user, max_damage_date, last_activity = result
                
                cur.execute("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM chat_user_stats 
                    WHERE chat_id = %s
                """, (chat_id,))
                total_users = cur.fetchone()[0] or 0
                
                cur.execute("""
                    SELECT COUNT(DISTINCT user_id) 
                    FROM chat_user_stats 
                    WHERE chat_id = %s AND last_shlep >= CURRENT_DATE
                """, (chat_id,))
                active_today = cur.fetchone()[0] or 0
                
                return {
                    'total_shleps': total_shleps,
                    'max_damage': max_damage,
                    'max_damage_user': max_damage_user,
                    'max_damage_date': max_damage_date,
                    'last_activity': last_activity,
                    'total_users': total_users,
                    'active_today': active_today
                }
            return None

def get_chat_top_users(chat_id: int, limit=10):
    if not DATABASE_URL:
        if chat_id in fake_db.chat_stats:
            users = []
            for uid, data in fake_db.chat_stats[chat_id]['users'].items():
                users.append((data['username'], data['shlep_count']))
            users.sort(key=lambda x: x[1], reverse=True)
            return users[:limit]
        return []
    
    with get_connection() as conn:
        if conn is None:
            return []
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, shlep_count 
                FROM chat_user_stats 
                WHERE chat_id = %s 
                ORDER BY shlep_count DESC 
                LIMIT %s
            """, (chat_id, limit))
            return cur.fetchall()

def create_chat_vote(chat_id: int, message_id: int, initiator_id: int, 
                     initiator_name: str, question: str):
    with get_connection() as conn:
        if conn is None:
            return None
        
        with conn.cursor() as cur:
            ends_at = datetime.now() + timedelta(minutes=5)
            
            cur.execute("""
                INSERT INTO chat_votes 
                (chat_id, message_id, initiator_id, initiator_name, question, ends_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING vote_id
            """, (chat_id, message_id, initiator_id, initiator_name, question, ends_at))
            
            vote_id = cur.fetchone()[0]
            conn.commit()
            return vote_id

def get_chat_vote(vote_id: int):
    with get_connection() as conn:
        if conn is None:
            return None
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM chat_votes 
                WHERE vote_id = %s AND is_active = TRUE
            """, (vote_id,))
            result = cur.fetchone()
            return result

def update_chat_vote(vote_id: int, user_id: int, vote_type: str):
    with get_connection() as conn:
        if conn is None:
            return False
        
        with conn.cursor() as cur:
            if vote_type == 'yes':
                cur.execute("""
                    UPDATE chat_votes 
                    SET yes_votes = yes_votes + 1
                    WHERE vote_id = %s
                """, (vote_id,))
            else:
                cur.execute("""
                    UPDATE chat_votes 
                    SET no_votes = no_votes + 1
                    WHERE vote_id = %s
                """, (vote_id,))
            
            conn.commit()
            return True

def assign_chat_role(chat_id: int, user_id: int, role_type: str, 
                     role_name: str, duration_hours: int = 24):
    with get_connection() as conn:
        if conn is None:
            return False
        
        with conn.cursor() as cur:
            expires_at = datetime.now() + timedelta(hours=duration_hours)
            
            cur.execute("""
                INSERT INTO chat_roles (chat_id, user_id, role_type, role_name, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (chat_id, user_id, role_type) 
                DO UPDATE SET 
                    role_name = EXCLUDED.role_name,
                    awarded_at = CURRENT_TIMESTAMP,
                    expires_at = EXCLUDED.expires_at
            """, (chat_id, user_id, role_type, role_name, expires_at))
            
            conn.commit()
            return True

def get_user_roles(chat_id: int, user_id: int):
    with get_connection() as conn:
        if conn is None:
            return []
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role_name 
                FROM chat_roles 
                WHERE chat_id = %s AND user_id = %s AND expires_at > CURRENT_TIMESTAMP
            """, (chat_id, user_id))
            results = cur.fetchall()
            return [r[0] for r in results]

def get_chat_roles_stats(chat_id: int):
    with get_connection() as conn:
        if conn is None:
            return {}
        
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role_type, COUNT(DISTINCT user_id) as count
                FROM chat_roles 
                WHERE chat_id = %s AND expires_at > CURRENT_TIMESTAMP
                GROUP BY role_type
            """, (chat_id,))
            results = cur.fetchall()
            
            stats = {}
            for role_type, count in results:
                stats[role_type] = count
            
            return stats

def close_connection_pool():
    global CONNECTION_POOL
    if CONNECTION_POOL:
        CONNECTION_POOL.closeall()
