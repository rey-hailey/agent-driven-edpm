-- 수료율: 기간 내 등록 코호트 중 completed_at이 채워진 비율 (L03 CP 규칙 적용 결과를 enrollments.completed_at에 기록한다고 가정)
-- 파라미터: {{from}}, {{to}} 등록일 기준 코호트, {{course}}
-- 기본 스키마: enrollments(learner_key, course_id, enrolled_at, expires_at, completed_at)
select
  count(*)                                                  as enrolled,
  sum(case when completed_at is not null then 1 else 0 end) as completed,
  round(sum(case when completed_at is not null then 1 else 0 end) * 100.0 / nullif(count(*), 0), 1) as completion_pct,
  round(avg(case when completed_at is not null then julianday(completed_at) - julianday(enrolled_at) end), 1) as avg_days_to_complete
from enrollments
where course_id = '{{course}}' and enrolled_at between '{{from}}' and '{{to}}';
