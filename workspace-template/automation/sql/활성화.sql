-- 활성화: 가입 후 7일 안에 핵심 행동(기본: 단원 완료 1회 이상)을 한 학습자 비율 (N03 GT-02, F02 목표 지표 후보)
-- 파라미터: {{from}}, {{to}} 가입일 범위, {{event}} 핵심 행동 이벤트명 (예: lesson_completed), {{n}} 최소 횟수
select
  count(*) as joined,
  sum(activated) as activated,
  round(sum(activated) * 100.0 / nullif(count(*), 0), 1) as activation_pct
from (
  select l.learner_key,
         case when (
           select count(*) from learning_events e
           where e.learner_key = l.learner_key and e.event = '{{event}}'
             and julianday(e.event_time) - julianday(l.joined_at) between 0 and 7
         ) >= {{n}} then 1 else 0 end as activated
  from learners l where l.joined_at between '{{from}}' and '{{to}}'
);
