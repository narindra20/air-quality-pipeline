
DROP TABLE IF EXISTS fact_air_quality CASCADE;
DROP TABLE IF EXISTS dim_city CASCADE;
DROP TABLE IF EXISTS dim_time CASCADE;

CREATE TABLE dim_city (
                          city_id SERIAL PRIMARY KEY,
                          city_name VARCHAR(100) NOT NULL UNIQUE,
                          country VARCHAR(100) NOT NULL,
                          latitude NUMERIC(8, 4) NOT NULL,
                          longitude NUMERIC(8, 4) NOT NULL
);


CREATE TABLE dim_time (
                          time_id VARCHAR(13) PRIMARY KEY,
                          timestamp_utc TIMESTAMP NOT NULL,
                          date_day DATE NOT NULL,
                          hour INT NOT NULL CHECK (hour BETWEEN 0 AND 23),
    day_of_week INT NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),
    day_name VARCHAR(20) NOT NULL,
    month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
    year INT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE fact_air_quality (
                                  fact_id BIGSERIAL PRIMARY KEY,
                                  city_id INT NOT NULL REFERENCES dim_city(city_id) ON DELETE CASCADE,
                                  time_id VARCHAR(13) NOT NULL REFERENCES dim_time(time_id) ON DELETE CASCADE,
                                  aqi NUMERIC(5, 2),
                                  pm2_5 NUMERIC(8, 2),
                                  pm10 NUMERIC(8, 2),
                                  no2 NUMERIC(8, 2),
                                  o3 NUMERIC(8, 2),
                                  so2 NUMERIC(8, 2),
                                  co NUMERIC(8, 2),
                                  CONSTRAINT unique_city_time_measure UNIQUE (city_id, time_id)
);

CREATE INDEX idx_fact_city ON fact_air_quality(city_id);
CREATE INDEX idx_fact_time ON fact_air_quality(time_id);