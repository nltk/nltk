create table LPATH_TABLE (
sid	int,
tid	int,
id	int,
pid	int,
l	int,
r	int,
d	int,
type	varchar(32),
name	varchar(32),
value	varchar(64)
);

create index TABLE_all_idx on LPATH_TABLE (name,type,sid,tid,id,pid,l,r,d,value);
create index TABLE_sid_idx on LPATH_TABLE (sid, tid, l, r, d);
create index TABLE_value_idx on LPATH_TABLE (value, type, name, sid, tid, pid);

