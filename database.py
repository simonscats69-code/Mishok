def init_db():
    """Инициализация всех таблиц"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # ... существующие таблицы ...
            
            # XP система
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_xp (
                    user_id BIGINT PRIMARY KEY,
                    xp BIGINT DEFAULT 0,
                    last_updated TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS xp_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    xp_amount INT,
                    reason VARCHAR(100),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS level_ups (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    level INT,
                    reward INT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Навыки
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_skills (
                    user_id BIGINT,
                    skill_id VARCHAR(50),
                    level INT DEFAULT 0,
                    PRIMARY KEY (user_id, skill_id)
                )
            """)
            
            # Детальная статистика
            cur.execute("""
                CREATE TABLE IF NOT EXISTS detailed_stats (
                    user_id BIGINT,
                    stat_date DATE,
                    hour INT,
                    shlep_count INT DEFAULT 0,
                    PRIMARY KEY (user_id, stat_date, hour)
                )
            """)
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS shlep_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    shlep_count INT,
                    avg_speed FLOAT,  -- шлёпков в минуту
                    max_combo INT
                )
            """)
            
            # Рекорды
            cur.execute("""
                CREATE TABLE IF NOT EXISTS records (
                    record_type VARCHAR(50),
                    user_id BIGINT,
                    value FLOAT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (record_type)
                )
            """)
            
            # Глобальные цели
            cur.execute("""
                CREATE TABLE IF NOT EXISTS global_goals (
                    id SERIAL PRIMARY KEY,
                    goal_name VARCHAR(100),
                    target_value BIGINT,
                    current_value BIGINT DEFAULT 0,
                    reward_type VARCHAR(50),
                    reward_value INT,
                    is_active BOOLEAN DEFAULT TRUE,
                    start_date DATE,
                    end_date DATE
                )
            """)
            
            # События
            cur.execute("""
                CREATE TABLE IF NOT EXISTS active_events (
                    event_type VARCHAR(50),
                    multiplier FLOAT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    description TEXT
                )
            """)
            
            conn.commit()
