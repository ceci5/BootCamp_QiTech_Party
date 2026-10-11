CREATE TABLE sample_entity_status(
    id		                        SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);

INSERT INTO sample_entity_status (enumerator) VALUES
('created'),
('pending'),
('success'),
('failed');

CREATE TABLE sample_entity(
    id                              SERIAL PRIMARY KEY,
    sample_entity_key               CHAR(36) NOT NULL,
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    sample_entity_data              JSONB NOT NULL,
    name                            VARCHAR(255) NOT NULL,
    email                           VARCHAR(255) NOT NULL,
    document_number                 CHAR(14) NOT NULL,
    birthdate                       DATE NOT NULL,
    counter                         INTEGER NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW()),
    UNIQUE(sample_entity_key),
    UNIQUE(document_number),
    UNIQUE(email)
);

CREATE TABLE sample_entity_status_event(
    id                              SERIAL PRIMARY KEY,
    sample_entity_id                INTEGER NOT NULL REFERENCES sample_entity(id),
    status_id                       INTEGER NOT NULL REFERENCES sample_entity_status(id),
    event_datetime                  TIMESTAMP NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

-- ====================================================================
-- CADASTRO -- acrescentado pelo time. Nada acima desta linha mudou.
-- ====================================================================

CREATE FUNCTION append_only_guard() RETURNS TRIGGER AS $func$
BEGIN
    -- sem o caractere de porcentagem: ele quebra o DbUtils.rollback() (spec 03, P2, 2026-10-11)
    RAISE EXCEPTION USING MESSAGE = TG_TABLE_NAME || ' e append-only';
END;
$func$ LANGUAGE plpgsql;

CREATE TABLE party_status(
    id              SERIAL PRIMARY KEY,
    enumerator      VARCHAR(50) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(enumerator)
);
INSERT INTO party_status (enumerator) VALUES ('pending'), ('active'), ('rejected');

CREATE TABLE party(
    id              SERIAL PRIMARY KEY,
    party_key       CHAR(36) NOT NULL,
    party_status_id INTEGER NOT NULL REFERENCES party_status(id),
    name            VARCHAR(255) NOT NULL,
    -- digitos apenas: 11 = pessoa fisica, 14 = pessoa juridica
    document_number VARCHAR(14) NOT NULL,
    pix_key         VARCHAR(77),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(party_key),
    UNIQUE(document_number),
    CHECK (LENGTH(document_number) IN (11, 14))
);

CREATE TABLE party_status_event(
    id              SERIAL PRIMARY KEY,
    party_id        INTEGER NOT NULL REFERENCES party(id),
    from_status_id  INTEGER REFERENCES party_status(id),        -- nulo ao nascer
    to_status_id    INTEGER NOT NULL REFERENCES party_status(id),
    actor           VARCHAR(255) NOT NULL,
    reason          VARCHAR(255),
    trace_id        VARCHAR(64) NOT NULL,
    event_datetime  TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT(NOW())
);

-- A plataforma: a parte, com chave fixa que os tres conhecem (o cliente 9c9c... e da fatia 04)
INSERT INTO party (party_key, party_status_id, name, document_number, pix_key)
SELECT '99999999-9999-4999-8999-999999999999', id, 'Plataforma', '11222333000181', 'plataforma@example.com'
FROM party_status WHERE enumerator = 'active';

INSERT INTO party_status_event (party_id, from_status_id, to_status_id, actor, reason, trace_id, event_datetime)
SELECT p.id, NULL, p.party_status_id, 'seed', 'plataforma semeada', 'seed', NOW()
FROM party p WHERE p.party_key = '99999999-9999-4999-8999-999999999999';

-- Imutabilidade da trilha de estado: dois gatilhos (o de linha nao
-- dispara em TRUNCATE). Moram AQUI porque a suite recria o schema daqui
CREATE TRIGGER party_status_event_no_change
    BEFORE UPDATE OR DELETE ON party_status_event
    FOR EACH ROW EXECUTE FUNCTION append_only_guard();
CREATE TRIGGER party_status_event_no_truncate
    BEFORE TRUNCATE ON party_status_event
    FOR EACH STATEMENT EXECUTE FUNCTION append_only_guard();

-- O cliente da plataforma (fatia 04): uma parte juridica que paga pelo
-- servico. Sem estado proprio: o estado que vale e o da parte (06, item 3)
CREATE TABLE client(
    id                      SERIAL PRIMARY KEY,
    client_key              CHAR(36) NOT NULL,
    party_id                INTEGER NOT NULL REFERENCES party(id),
    -- quanto do aluguel a plataforma cobra DESTA imobiliaria; paga por ela
    platform_fee_percentage NUMERIC(7,4) NOT NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT(NOW()),
    UNIQUE(client_key),
    UNIQUE(party_id),
    CHECK (platform_fee_percentage >= 0 AND platform_fee_percentage < 100)
);

-- A plataforma tambem e cliente, com chave fixa que os tres conhecem
INSERT INTO client (client_key, party_id, platform_fee_percentage)
SELECT '9c9c9c9c-9c9c-49c9-89c9-9c9c9c9c9c9c', id, 0
FROM party WHERE party_key = '99999999-9999-4999-8999-999999999999';
