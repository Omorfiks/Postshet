BEGIN TRANSACTION;
CREATE TABLE posts
                 (id SERIAL PRIMARY KEY,
                  telegram_id BIGINT UNIQUE,
                  media_type TEXT,
                  media_path TEXT,
                  caption TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
INSERT INTO posts VALUES(1,1677,'photo','1677_115800.jpg','','2026-02-10 08:58:05');
CREATE TABLE reactions
                 (id SERIAL PRIMARY KEY,
                  post_id INTEGER,
                  reaction_type TEXT,
                  count INTEGER DEFAULT 1,
                  FOREIGN KEY (post_id) REFERENCES posts(id));
INSERT INTO reactions VALUES(17,1,'heart',2);
CREATE TABLE channel_info
                 (id INTEGER PRIMARY KEY,
                  name TEXT,
                  avatar_url TEXT,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
INSERT INTO channel_info VALUES(1,'╨┐╨╛╤Б╤В╤Й╨╕╤В╨╜╨╛╤Б╤В╤М','/uploads/channel_avatar_-1002343587948.jpg','2026-02-09 14:13:04');
CREATE TABLE users
                 (id SERIAL PRIMARY KEY,
                  telegram_id BIGINT UNIQUE NOT NULL,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  photo_url TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
INSERT INTO users VALUES(1,6176398479,'Roman_Babko','╨а╨╛╨╝╨░╨╜','╨С╨░╨▒╨║╨╛','','2026-02-10 10:17:58');
INSERT INTO users VALUES(8,1414996308,'IncredibleDreamer','╨б╨┐╨╛╨║╨╛╨╣╤Б╤В╨▓╨╕╨╡','','/uploads/user_avatar_1414996308.jpg','2026-02-10 13:13:30');
CREATE TABLE user_reactions
                 (post_id INTEGER NOT NULL,
                  user_id TEXT NOT NULL,
                  reaction_type TEXT NOT NULL,
                  PRIMARY KEY (post_id, user_id),
                  FOREIGN KEY (post_id) REFERENCES posts(id));
INSERT INTO user_reactions VALUES(1,'tg_1414996308','heart');
INSERT INTO user_reactions VALUES(1,'tg_6176398479','heart');
CREATE TABLE login_tokens
                 (token TEXT PRIMARY KEY,
                  telegram_id BIGINT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
INSERT INTO login_tokens VALUES('18F6G6gGjQHbHTLuifxmt_skBgi7j9ua8EdXgs_WiLc',1414996308,'2026-02-10 13:22:38');
INSERT INTO login_tokens VALUES('QZU9iA_vFdtTEevTkglQo1pFclQjyCo3FzPkZWAcDLU',1414996308,'2026-02-10 13:43:09');
COMMIT;
