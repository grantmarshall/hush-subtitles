-- Table for an individual translation session
CREATE TABLE sessions (
    id BIGSERIAL PRIMARY KEY,
    active BOOLEAN,
    creation_time TIMESTAMP,
    last_translation TIMESTAMP
);

-- Table for audio data in a translation session, rows represent 1s of audio data
CREATE TABLE audio_data (
    session_id BIGSERIAL REFERENCES sessions(session_id),
    start_ts TIMESTAMP,
    d BYTEA
);

-- Table for translations produced for sessions
CREATE TABLE translations (
    session_id BIGSERIAL REFERENCES sessions(session_id),
    start_ts TIMESTAMP,
    translation TEXT
);
