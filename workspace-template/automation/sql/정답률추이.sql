-- 정답률 추이: 주차별 문항 시도 정답률 (학습 효과의 거친 신호. 효과크기는 metrics.py effect-size로 비교집단과 계산)
-- 파라미터: {{from}}, {{to}}, {{course}}
-- 기본 스키마: learning_events(event='attempt_submitted', value=1 정답/0 오답)
select strftime('%Y-W%W', event_time) as week,
       count(*) as attempts,
       count(distinct learner_key) as learners,
       round(avg(value) * 100, 1) as correct_pct
from learning_events
where course_id = '{{course}}' and event = 'attempt_submitted' and date(event_time) between '{{from}}' and '{{to}}'
group by week order by week;
