-- 주간 코호트 리텐션: 가입 주차별로 n주 차에 학습 이벤트가 1건 이상인 학습자 비율 (N03 GT-01 리텐션 곡선, E07 참여 지표)
-- 파라미터: {{from}}, {{to}} 가입일 범위, {{weeks}} 추적 주 수 (예: 8)
-- 기본 스키마: learners(learner_key, joined_at), learning_events(event_time, learner_key)
-- 읽는 법: 같은 cohort 행에서 week가 커질수록 retained_pct가 어디서 평탄해지는지 본다
with cohort as (
  select learner_key, date(joined_at, 'weekday 0', '-6 days') as cohort_week, joined_at
  from learners where joined_at between '{{from}}' and '{{to}}'
),
weeks as (
  select 0 as week union all select week + 1 from weeks where week < {{weeks}}
),
activity as (
  select c.cohort_week, w.week,
         count(distinct case when exists (
           select 1 from learning_events e
           where e.learner_key = c.learner_key
             and julianday(e.event_time) - julianday(c.joined_at) between w.week * 7 and w.week * 7 + 6
         ) then c.learner_key end) as retained,
         count(distinct c.learner_key) as size
  from cohort c cross join weeks w
  group by c.cohort_week, w.week
)
select cohort_week, size, week, retained, round(retained * 100.0 / size, 1) as retained_pct
from activity order by cohort_week, week;
