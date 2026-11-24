-- The reference answers of the SQL test of DE17, on data/raw/app-events/events.csv. One statement for each question.

-- Question 1: how many different people made a purchase, and how many purchase events are there?
SELECT count(DISTINCT user_id) AS people, count(*) AS purchases
FROM 'data/raw/app-events/events.csv'
WHERE event_name = 'purchase';

-- Question 2: in which hour of the day (as the file records it) are there most events, and how many?
SELECT hour(event_ts) AS hour, count(*) AS events
FROM 'data/raw/app-events/events.csv'
GROUP BY hour
ORDER BY events DESC, hour
LIMIT 1;

-- Question 3: of the people who signed up in January 2026, how many were there, and how many had a session_start within 7 days after signing up?
WITH signups AS (
    SELECT user_id, min(event_ts) AS signed_up
    FROM 'data/raw/app-events/events.csv'
    WHERE event_name = 'signup_complete' AND event_ts < TIMESTAMP '2026-02-01'
    GROUP BY user_id
)
SELECT count(*) AS signups,
       count(*) FILTER (WHERE EXISTS (
           SELECT 1 FROM 'data/raw/app-events/events.csv' AS e
           WHERE e.user_id = s.user_id AND e.event_name = 'session_start'
             AND e.event_ts >= s.signed_up AND e.event_ts < s.signed_up + INTERVAL 7 DAY
       )) AS active_in_week_1
FROM signups AS s;

-- Question 4: which is the last day of the seven days with the most signups (signup_complete events), and how many signups did they have?
WITH daily AS (
    SELECT CAST(event_ts AS DATE) AS day, count(*) AS signups
    FROM 'data/raw/app-events/events.csv'
    WHERE event_name = 'signup_complete'
    GROUP BY day
)
SELECT day AS last_day, sum(signups) OVER (ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS seven_days
FROM daily
ORDER BY seven_days DESC, day
LIMIT 1;

-- Question 5: how many events reached the server more than one day after they happened, and how late was the latest?
SELECT count(*) FILTER (WHERE received_at - event_ts > INTERVAL 1 DAY) AS over_a_day,
       max(received_at - event_ts) AS latest
FROM 'data/raw/app-events/events.csv';
