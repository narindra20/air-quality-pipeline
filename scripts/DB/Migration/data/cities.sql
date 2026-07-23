INSERT INTO dim_city (city_name, country, latitude, longitude)
VALUES
    ('Paris', 'France', 48.8566, 2.3522),
    ('Marseille', 'France', 43.2965, 5.3698),
    ('Lyon', 'France', 45.7640, 4.8357),
    ('Toulouse', 'France', 43.6047, 1.4442),
    ('Nice', 'France', 43.7102, 7.2620)
    ON CONFLICT (city_name) DO NOTHING;