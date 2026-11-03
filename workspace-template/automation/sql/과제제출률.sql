-- 과제 제출률: 기간 내 출제된 과제(unit_id = 과제 ID) 대비 제출 이벤트 비율. 교사·강사 도입 지표(E07 M-3x), L04 과제 운영
-- 파라미터: {{from}}, {{to}}, {{course}}
-- 기본 스키마: learning_events(event='assignment_submitted', unit_id=과제 ID). 출제 수는 과제별 등록 학습자 수로 근사
with assigned as (
  select e.unit_id as assignment_id, (select count(*) from enrollments en where en.course_id = '{{course}}') as expected
  from learning_events e where e.course_id = '{{course}}' and e.event = 'assignment_submitted'
    and date(e.event_time) between '{{from}}' and '{{to}}'
  group by e.unit_id
),
submitted as (
  select unit_id as assignment_id, count(distinct learner_key) as submitted
  from learning_events where course_id = '{{course}}' and event = 'assignment_submitted'
    and date(event_time) between '{{from}}' and '{{to}}'
  group by unit_id
)
select a.assignment_id, a.expected, s.submitted, round(s.submitted * 100.0 / nullif(a.expected, 0), 1) as submit_pct
from assigned a join submitted s using (assignment_id) order by a.assignment_id;
