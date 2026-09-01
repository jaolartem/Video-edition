import sqlite3
import basedatos

SQL = """
drop view if exists v_verdad;
create view v_verdad as

-- **Una fila por decisión viva, con su sitio y su fecha.**
--
-- Jaime: *«¿puedes hacer una tabla o una vista que se vaya actualizando o
-- moviendo con el paso de las decisiones? con eso la dejamos en memoria»*.
-- Es una vista y no una tabla a propósito: una tabla habría que mantenerla al
-- día, y mantener al día una copia de las decisiones es exactamente el fallo
-- que esto viene a cerrar (C-142). La vista se mueve sola porque no guarda
-- nada: mira donde de verdad viven.
--
-- Lo que NO puede estar aquí es lo que no vive en la base: si el vídeo
-- montado existe y si es más nuevo que su corte. Eso lo dice `avanzar.py`,
-- porque la verdad de ese hecho es un fichero en disco.

select 'libreto'  as decision,
       v.slug     as pieza,
       l.orden    as etapa,
       substr(replace(l.texto, char(10), ' '), 1, 70) as valor,
       null       as quien,
       null       as fecha,
       'tabla libreto' as vive_en
  from libreto l join video v on v.id = l.video_id

union all
select 'tablero', ed.video_slug, ed.etapa_orden,
       substr(ed.tablero, 1, 70), ed.quien, ed.fecha,
       'escena_desc.tablero'
  from escena_desc ed
 where ed.tablero is not null and ed.tablero <> ''

union all
select 'descripcion', ed.video_slug, ed.etapa_orden,
       substr(replace(coalesce(ed.que_pasa,''), char(10), ' '), 1, 70),
       ed.quien, ed.fecha, 'escena_desc'
  from escena_desc ed

union all
select 'cifra', v.slug, d.etapa_orden,
       substr(d.cifra, 1, 50) || ' [' || coalesce(d.respalda,'?') || ']',
       null, d.fecha, 'tabla dato'
  from dato d join video v on v.id = d.video_id

union all
select 'corte', v.slug, c.orden,
       printf('%.2f - %.2f  %s', c.desde, c.hasta, coalesce(c.toma,'')),
       c.quien, c.fecha, 'tabla corte_fijo'
  from corte_fijo c join video v on v.id = c.video_id

union all
select 'fase', v.slug, null, f.nombre, null, vf.entro, 'tabla video_fase'
  from video_fase vf
  join video v on v.id = vf.video_id
  join fase f  on f.id = vf.fase_id
 where vf.id = (select max(id) from video_fase w where w.video_id = vf.video_id)

union all
select 'sube a Jaime', r.video_slug, null,
       substr(replace(r.que, char(10), ' '), 1, 70), null, r.fecha,
       'tabla revision'
  from revision r
 where r.estado = 'sube'

union all
-- **La grabacion, que es lo unico que no se puede rehacer.** Jaime: *«con esa
-- queda un historico de los videos grabados»*. Una cinta existe aunque ninguna
-- pieza la use todavia, y esa es justo la que se pierde de vista: la septima
-- estuvo en disco sin aparecer en ningun listado.
select 'grabacion', coalesce(
         (select group_concat(distinct v2.slug)
            from corte_fijo c2 join video v2 on v2.id = c2.video_id
           where c2.toma = t.nombre), 'sin pieza'),
       (select count(*) from corte_fijo c3 where c3.toma = t.nombre),
       t.nombre, null, null, 'tabla toma'
  from toma t;
"""

con = basedatos.abrir("ads/decisiones.db")
con.executescript(SQL)
con.commit()
n = con.execute("select count(*) from v_verdad").fetchone()[0]
print(f"v_verdad creada · {n} decisiones vivas")
for r in con.execute("select decision, count(*) from v_verdad group by decision"
                     " order by 2 desc"):
    print(f"  {r[0]:14} {r[1]:4}")
con.close()
