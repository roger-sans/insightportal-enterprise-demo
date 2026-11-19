CREATE TABLE dim_site (site_id VARCHAR(20) PRIMARY KEY, label VARCHAR(80) NOT NULL);
CREATE TABLE dim_month (month VARCHAR(7) PRIMARY KEY, calendar_year INTEGER NOT NULL);
CREATE TABLE mart_finance (
    month VARCHAR(7) NOT NULL REFERENCES dim_month(month), site_id VARCHAR(20) NOT NULL REFERENCES dim_site(site_id),
    revenue_cents BIGINT NOT NULL, gross_profit_cents BIGINT NOT NULL, PRIMARY KEY (month, site_id)
);
CREATE TABLE mart_commercial (
    month VARCHAR(7) NOT NULL REFERENCES dim_month(month), site_id VARCHAR(20) NOT NULL REFERENCES dim_site(site_id),
    bookings_cents BIGINT NOT NULL, won INTEGER NOT NULL, closed INTEGER NOT NULL, PRIMARY KEY (month, site_id)
);
CREATE TABLE mart_operations (
    month VARCHAR(7) NOT NULL REFERENCES dim_month(month), site_id VARCHAR(20) NOT NULL REFERENCES dim_site(site_id),
    on_time INTEGER NOT NULL, completed INTEGER NOT NULL, PRIMARY KEY (month, site_id)
);
CREATE TABLE mart_people (
    month VARCHAR(7) NOT NULL REFERENCES dim_month(month), site_id VARCHAR(20) NOT NULL REFERENCES dim_site(site_id),
    trained INTEGER NOT NULL, eligible INTEGER NOT NULL, absence_days INTEGER NOT NULL,
    scheduled_days INTEGER NOT NULL, PRIMARY KEY (month, site_id)
);
CREATE TABLE publication (
    domain VARCHAR(20) PRIMARY KEY, contract_version VARCHAR(16) NOT NULL,
    published_at VARCHAR(30) NOT NULL, through_month VARCHAR(7) NOT NULL
);
