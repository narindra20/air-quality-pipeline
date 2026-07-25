
CREATE TABLE IF NOT EXISTS dim_city (
                                        city_id SERIAL PRIMARY KEY,
                                        city_name VARCHAR(100) NOT NULL UNIQUE,
    country VARCHAR(100) NOT NULL,
    latitude NUMERIC(8, 4) NOT NULL,
    longitude NUMERIC(8, 4) NOT NULL
    );
--
CREATE TABLE IF NOT EXISTS dim_time (
                                        time_id VARCHAR(13) PRIMARY KEY, -- Format: YYYY-MM-DD-HH
    timestamp_utc TIMESTAMP NOT NULL,
    date_day DATE NOT NULL,
    hour INT NOT NULL,
    day_of_week INT NOT NULL,
    day_name VARCHAR(20) NOT NULL,
    month INT NOT NULL,
    year INT NOT NULL,
    is_weekend BOOLEAN NOT NULL
    );

CREATE TABLE IF NOT EXISTS fact_air_quality (
                                                fact_id BIGSERIAL PRIMARY KEY,
                                                city_id INT NOT NULL REFERENCES dim_city(city_id),
    time_id VARCHAR(13) NOT NULL REFERENCES dim_time(time_id),
    aqi NUMERIC(5, 2),
    pm2_5 NUMERIC(8, 2),
    pm10 NUMERIC(8, 2),
    no2 NUMERIC(8, 2),
    o3 NUMERIC(8, 2),
    so2 NUMERIC(8, 2),
    co NUMERIC(8, 2),
    CONSTRAINT unique_city_time UNIQUE (city_id, time_id)
    );