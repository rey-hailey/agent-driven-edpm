-- 진도율: 기간 내 학습자별 완료 단원 수 / 과정 전체 단원 수 (L03 PG 공식의 기본형)
-- 파라미터: {{from}}, {{to}} (YYYY-MM-DD), {{course}} 과정 ID. 전체 단원 수는 과정 메타가 없을 때 이벤트에서 관측된 최대 단원 수로 대체
-- 기본 스키마: learning_events(event_time, learner_key, event='lesson_completed', course_id, unit_id)
-- 검증: sample-db에서 손계산 10명 일치 (2026-10)
with units as (
  select count(distinct unit_id) as total from learning_events where course_id = '{{course}}' and event = 'lesson_completed'
),
per_learner as (
  select learner_key, count(distinct unit_id) as done_units
  from learning_events
  where course_id = '{{course}}' and event = 'lesson_completed'
    and date(event_time) between '{{from}}' and '{{to}}'
  group by learner_key
)
select
  count(*)                                   as learners,
  (select total from units)                  as total_units,
  round(avg(done_units * 1.0 / (select total from units)) * 100, 1) as avg_progress_pct,
  sum(case when done_units * 1.0 / (select total from units) >= 0.8 then 1 else 0 end) as learners_over_80pct
from per_learner;
