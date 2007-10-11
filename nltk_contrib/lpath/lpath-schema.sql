create table TABLE (
sid     int,
tid     int,
id      int,
pid     int,
l       int,
r       int,
d       int,
type    varchar(32),
name    varchar(32),
value   varchar(64)
);

create index TABLE_all_idx on TABLE (name,type,sid,tid,id,pid,l,r,d,value);
create index TABLE_sid_idx on TABLE (sid, tid, l, r, d);
create index TABLE_value_idx on TABLE (value, type, name, sid, tid, pid);
