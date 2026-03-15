-- PART 1

-- 1 Вывести всю информацию из таблицы ticket_flights
SELECT * 
FROM booking.ticket_flights

-- 2 Вывести номера билетов и их стоимость из таблицы ticket_flights, где класс бронирования Business
SELECT ticket_no, amount
FROM booking.ticket_flights
WHERE fare_conditions = 'Business';

-- 3 Вывести коды аэропортов, которые находятся во временной зоне Europe/Moscow
SELECT DISTINCT(airport_code)
FROM booking.airports_data
WHERE timezone = 'Europe/Moscow'

-- 4 Вывести всю информацию из таблицы flights, где номер полета является «PG0216»
SELECT * 
FROM booking.flights
WHERE flight_no = 'PG0216'

-- 5 Вывести из таблицы flights все рейсы из Домодедово в Пулково
SELECT * 
FROM booking.flights
WHERE departure_airport = 'DME' and arrival_airport = 'LED'

-- 6 Вывести из таблицы flights рейсы, вылет которых был запланирован в интервале
-- с 10 февраля 2017 по 10 апреля 2017

SELECT * 
FROM booking.flights
WHERE scheduled_departure BETWEEN '2017-02-10' and '2017-04-10'

-- 7 Вывести названия моделей самолётов на английском языке, дальность полета которых менее 5000 км
SELECT model->> 'en' as model_eng
FROM booking.aircrafts_data
WHERE range < 5000

-- 8 Вывести всю информацию из таблицы tickets, отсортированную по колонке passenger_name в
-- обратном порядке и ограничением выборки в 100 записей
SELECT *
FROM booking.tickets
ORDER BY passenger_name DESC LIMIT 100

-- 9 Вывести из таблицы tickets поля ticket_no и passenger_name, где имя пассажира VIKTORIYA SMIRNOVA
SELECT ticket_no, passenger_name
FROM booking.tickets
WHERE passenger_name = 'VIKTORIYA SMIRNOVA'

-- 10 Вывести из таблицы tickets идентификаторы, имена и фамилии всех пассажиров, фамилии которых 
-- заканчиваются на «NOV» или «OVA», отсортировав их сначала по номеру билета, а затем по имени
-- пассажира в обратном порядке

SELECT ticket_no, passenger_name, passenger_id
FROM booking.tickets
WHERE passenger_name LIKE '%NOV' OR passenger_name LIKE '%OVA'
ORDER BY ticket_no ASC, passenger_name DESC

-- PART 2

-- 1 Подсчитать общее количество самолетов в таблице aircrafts_data
SELECT COUNT(aircraft_code) AS aircraft_amount
FROM booking.aircrafts_data

-- 2 Вычислить среднюю дальность полета самолетов
SELECT AVG(range) AS mean_range
FROM booking.aircrafts_data

-- 3 Найти максимальную дальность полета среди всех самолетов
SELECT MAX(range) AS max_range
FROM booking.aircrafts_data

-- 4 Подсчитать общее количество аэропортов в таблице 
SELECT COUNT(DISTINCT(airport_code)) AS airports_amount
FROM booking.airports_data

-- 5 Вычислить среднюю, медиану и моду стоимости бронирования
SELECT	ROUND(AVG(total_amount)) as average_price, 
		PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_amount) as median_price, 
		MODE() WITHIN GROUP (ORDER BY total_amount)  as mode_price
FROM booking.bookings

-- 6 Найти первые пять самых дорогих бронирований
SELECT *
FROM booking.bookings
ORDER BY total_amount DESC
LIMIT 5

-- 7 Подсчитать общее количество посадочных талонов
SELECT COUNT(*) AS boarding_pass_count
FROM booking.boarding_passes

-- 8 Вычислить суммарную стоимость всех билетов класса комфорт
SELECT SUM(amount)
FROM booking.ticket_flights
WHERE fare_conditions = 'Comfort'

-- 9 Найти первый и последний рейсы
(SELECT flight_no, scheduled_departure
FROM booking.flights
ORDER BY scheduled_departure ASC
LIMIT 1)

UNION ALL

(SELECT flight_no, scheduled_departure
FROM booking.flights
ORDER BY scheduled_departure DESC
LIMIT 1);

-- 10 Найти среднюю стоимость билетов по классам обслуживания
SELECT	fare_conditions,
		ROUND(AVG(amount))
FROM booking.ticket_flights
GROUP BY fare_conditions



