-- Disposable technical prototype only, never an application migration.
CREATE TABLE unit (id uuid PRIMARY KEY, pool_id uuid NOT NULL);
CREATE TABLE reservation (
    id uuid PRIMARY KEY,
    unit_id uuid NOT NULL REFERENCES unit(id),
    during tstzrange NOT NULL,
    active boolean NOT NULL DEFAULT true,
    endangered boolean NOT NULL DEFAULT false,
    CHECK (NOT isempty(during) AND lower(during) IS NOT NULL AND upper(during) IS NOT NULL),
    CHECK (lower_inc(during) AND NOT upper_inc(during)),
    EXCLUDE USING gist (unit_id WITH =, during WITH &&) WHERE (active)
);
CREATE TABLE custody (
    id uuid PRIMARY KEY,
    unit_id uuid NOT NULL REFERENCES unit(id),
    reservation_id uuid NOT NULL REFERENCES reservation(id),
    issued_at timestamptz NOT NULL,
    expected_return timestamptz NOT NULL,
    returned_at timestamptz,
    CHECK (expected_return > issued_at),
    CHECK (returned_at IS NULL OR returned_at >= issued_at)
);
CREATE UNIQUE INDEX one_open_custody_per_unit ON custody(unit_id) WHERE returned_at IS NULL;
