CREATE DATABASE Customer;
USE Customer;

-- Customer table
CREATE TABLE Customers (
	customer_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    join_date DATE NOT NULL,
    segment	VARCHAR(50)
);

select * from Customers;


-- Transaction table
CREATE TABLE Transactions (
	transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT,
    date DATE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    product VARCHAR(100),
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);
SELECT * FROM Transactions;

-- Feedback table
CREATE TABLE Feedback (
	feedback_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT,
    date DATE NOT NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comments TEXT,
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);
select * from Feedback;

-- Retention_alerts table
CREATE TABLE Retention_Alerts (
	alert_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT,
    risk_level VARCHAR(20),
    action_taken VARCHAR(100),
    FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
);

select * from Retention_Alerts;
SELECT COUNT(*) FROM Retention_alerts WHERE risk_level = "High";

-- For inactive customer (no purchase in last 90 days)
SELECT c.customer_id, c.name
FROM Customers c
LEFT JOIN Transactions t ON c.customer_id = t.customer_id
WHERE t.date < DATE_SUB(CURDATE(), INTERVAL 90 DAY);

-- Average spend per customer
SELECT c.customer_id, c.name, avg(t.amount) AS total_spent
FROM Customers c
JOIN Transactions t
ON c.customer_id = t.customer_id
GROUP BY customer_id;

-- Feedback Sentiment Summery
SELECT c.customer_id, c.name, AVG(f.rating) AS average_rating, COUNT(f.feedback_id)
FROM Customers c
JOIN Feedback f
ON c.customer_id = f.customer_id
GROUP BY customer_id;

-- customer profile with activity summery
SELECT c.customer_id, c.segment,
       AVG(t.amount) AS avg_spend,
       MAX(t.date) AS last_purchase,
       AVG(f.rating) AS avg_rating
FROM Customers c
LEFT JOIN Transactions t ON c.customer_id = t.customer_id
LEFT JOIN Feedback f ON c.customer_id = f.customer_id
GROUP BY c.customer_id;


ALTER TABLE Customers ADD COLUMN churned INT DEFAULT 0;
ALTER TABLE Customers ADD COLUMN age INT;
ALTER TABLE Customers ADD COLUMN gender VARCHAR(10);
ALTER TABLE Customers ADD COLUMN location VARCHAR(100);

ALTER TABLE Retention_Alerts ADD COLUMN predicted_on DATETIME DEFAULT NOW();
ALTER TABLE Retention_Alerts ADD COLUMN confidence DECIMAL(5,2);

CREATE VIEW customer_ml_view AS
SELECT 
    c.customer_id,
    c.age,
    c.gender,
    c.location,
    c.segment,
    c.churned,
    COUNT(t.transaction_id) AS total_transactions,
    AVG(t.amount) AS avg_spend,
    MAX(t.date) AS last_purchase,
    AVG(f.rating) AS avg_rating
FROM Customers c
LEFT JOIN Transactions t ON c.customer_id = t.customer_id
LEFT JOIN Feedback f ON c.customer_id = f.customer_id
GROUP BY c.customer_id;

SELECT COUNT(*) FROM Customers;
SELECT COUNT(*) FROM Transactions;
SELECT COUNT(*) FROM Feedback;

SELECT * FROM customer_ml_view ;
SELECT * FROM Retention_Alerts;

SELECT c.name, c.segment, r.risk_level, r.confidence, r.action_taken, r.predicted_on
FROM retention_alerts r
JOIN customers c
ON r.customer_id = c.customer_id
ORDER BY predicted_on DESC
LIMIT 10;

ALTER TABLE Feedback ADD COLUMN sentiment VARCHAR(20);
SELECT feedback_id, customer_id, comments FROM Feedback;

describe customers;

SELECT * FROM customer_ml_view WHERE customer_id = 5;

SELECT feedback_id, comments, sentiment FROM Feedback LIMIT 10;


SELECT segment, churned, COUNT(*)
FROM Customers
GROUP BY segment, churned;

SELECT gender,
       churned,
       COUNT(*)
FROM Customers
GROUP BY gender, churned;

SELECT segment,
       gender,
       COUNT(*)
FROM Customers
GROUP BY segment, gender;
SELECT comments, sentiment 
from feedback where customer_id = %s, (customer_id, comments, feedback);

SELECT COUNT(*) AS total,
SUM(CASE WHEN sentiment = "Positive" THEN 1 ELSE 0 END) AS Positive,
SUM(CASE WHEN sentiment = "Negative"  THEN 1 ELSE 0 END) AS Negative,
SUM(CASE WHEN sentiment = "Neutral"  THEN 1 ELSE 0 END) AS Neutral
FROM feedback;

SELECT c.customer_id, c.name, c.email, c.age, c.gender, c.segment, c.location, c.join_date
FROM customers c
WHERE c.customer_id = 1;

SELECT COUNT(*) AS total_transactions, AVG(t.amount) AS average_spend, MAX(t.date) AS last_purchase
FROM transactions t WHERE customer_id = 4;

SELECT r.risk_level, r.confidence, r.predicted_on FROM retention_alerts AS r WHERE customer_id = 6;

describe feedback;

create table users(
	id int primary key auto_increment,
	username varchar(50) not null,
	password_hash varchar(255) not null
);
select * from users;

SELECT c.*, r.risk_level, r.confidence
FROM Customers c
LEFT JOIN (
    SELECT customer_id, risk_level, confidence
    FROM Retention_Alerts
    WHERE (customer_id, predicted_on) IN (
        SELECT customer_id, MAX(predicted_on)
        FROM Retention_Alerts
        GROUP BY customer_id
    )
) r ON c.customer_id = r.customer_id
ORDER BY c.customer_id
LIMIT 5;

SELECT * FROM Customers;
SELECT * FROM Transactions;
SELECT * FROM Feedback;
SELECT * FROM Retention_Alerts;

SELECT
total_transactions,
churned,
COUNT(*)
FROM customer_ml_view
GROUP BY total_transactions,churned;

DROP VIEW IF EXISTS customer_ml_view;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS Retention_Alerts;
DROP TABLE IF EXISTS Feedback;
DROP TABLE IF EXISTS Transactions;
DROP TABLE IF EXISTS Customers;
DROP TABLE IF EXISTS Users;

SET FOREIGN_KEY_CHECKS = 1;

describe customers;
ALTER TABLE customers
ADD UNIQUE(email);


SELECT sentiment, COUNT(*)
FROM feedback
GROUP BY sentiment;

SELECT churned, COUNT(*)
FROM customers
GROUP BY churned;

SELECT segment, COUNT(*)
FROM customers
GROUP BY segment;

SELECT sentiment, COUNT(*)
FROM feedback
GROUP BY sentiment;

SELECT *
FROM customer_ml_view
LIMIT 10;

SHOW CREATE VIEW customer_ml_view;
SHOW CREATE VIEW customer_ml_view;

SELECT customer_id, COUNT(*) AS transactions
FROM transactions
GROUP BY customer_id
ORDER BY transactions DESC
LIMIT 10;

SELECT customer_id, total_transactions
FROM customer_ml_view
ORDER BY total_transactions DESC
LIMIT 10;

DROP VIEW customer_ml_view;

CREATE VIEW customer_ml_view AS

SELECT
    c.customer_id,
    c.age,
    c.gender,
    c.location,
    c.segment,
    c.churned,

    COALESCE(t.total_transactions,0) AS total_transactions,
    COALESCE(t.avg_spend,0) AS avg_spend,
    t.last_purchase,

    COALESCE(f.avg_rating,0) AS avg_rating,

    COALESCE(s.avg_sentiment,0) AS sentiment_score

FROM customers c

LEFT JOIN
(
    SELECT
        customer_id,
        COUNT(*) AS total_transactions,
        AVG(amount) AS avg_spend,
        MAX(date) AS last_purchase
    FROM transactions
    GROUP BY customer_id
) t
ON c.customer_id = t.customer_id

LEFT JOIN
(
    SELECT
        customer_id,
        AVG(rating) AS avg_rating
    FROM feedback
    GROUP BY customer_id
) f
ON c.customer_id = f.customer_id

LEFT JOIN
(
    SELECT
        customer_id,
        AVG(
            CASE
                WHEN sentiment='Positive' THEN 1
                WHEN sentiment='Neutral' THEN 0
                WHEN sentiment='Negative' THEN -1
            END
        ) AS avg_sentiment
    FROM feedback
    GROUP BY customer_id
) s
ON c.customer_id = s.customer_id;

SELECT customer_id,total_transactions
FROM customer_ml_view
ORDER BY total_transactions DESC
LIMIT 10;

SELECT * FROM customer_ml_view LIMIT 10;

SELECT c.name, c.segment, r.risk_level, r.confidence, r.action_taken, r.predicted_on
        FROM retention_alerts r
        JOIN customers c
        ON r.customer_id = c.customer_id
        ORDER BY predicted_on DESC
        LIMIT 10;
select * from retention_alerts;
SELECT * FROM customer_ml_view LIMIT 1;

SELECT customer_id, name
FROM Customers
LIMIT 5;

INSERT INTO Retention_Alerts
(customer_id, risk_level, confidence, action_taken, predicted_on)
VALUES
(1, 'High Risk', 91.5, 'Pending', NOW()),
(3, 'Medium Risk', 74.2, 'Offer Coupon', NOW()),
(5, 'High Risk', 88.4, 'Call Customer', NOW());

SELECT * FROM Customers ORDER BY customer_id;

 select c.customer_id,
            c.name,
            c.segment,
            r.risk_level,
            r.confidence,
            r.action_taken,
            r.predicted_on

        FROM Customers c

        JOIN Retention_Alerts r
        ON c.customer_id = r.customer_id

        ORDER BY r.confidence DESC;
        
INSERT INTO Customers
(customer_id, name, email, join_date, segment, churned, age, gender, location)
VALUES
(251,'Aarav Joshi','aarav.joshi251@gmail.com','2025-02-12','Premium',0,32,'Male','Mumbai'),
(252,'Diya Mehta','diya.mehta252@gmail.com','2024-11-05','Regular',0,28,'Female','Delhi'),
(253,'Vivaan Shah','vivaan.shah253@gmail.com','2023-09-18','Premium',0,47,'Male','Pune'),
(254,'Anaya Kapoor','anaya.kapoor254@gmail.com','2025-04-01','Regular',0,24,'Female','Ahmedabad'),
(255,'Krish Patel','krish.patel255@gmail.com','2024-06-14','Premium',0,55,'Male','Hyderabad'),
(256,'Myra Nair','myra.nair256@gmail.com','2025-01-22','Regular',0,30,'Female','Bengaluru'),
(257,'Arjun Iyer','arjun.iyer257@gmail.com','2023-08-10','Premium',0,41,'Male','Chennai'),
(258,'Sara Khan','sara.khan258@gmail.com','2024-07-08','Regular',0,27,'Female','Mumbai'),
(259,'Kabir Verma','kabir.verma259@gmail.com','2025-03-15','Premium',0,50,'Male','Delhi'),
(260,'Ishita Rao','ishita.rao260@gmail.com','2024-10-21','Regular',0,36,'Female','Pune'),
(261,'Aditya Singh','aditya.singh261@gmail.com','2025-05-09','Regular',0,29,'Male','Jaipur'),
(262,'Riya Desai','riya.desai262@gmail.com','2023-12-01','Premium',0,45,'Female','Surat'),
(263,'Yash Malhotra','yash.malhotra263@gmail.com','2024-09-27','Regular',0,34,'Male','Lucknow'),
(264,'Kiara Sharma','kiara.sharma264@gmail.com','2025-06-17','Premium',0,39,'Female','Delhi'),
(265,'Dev Bansal','dev.bansal265@gmail.com','2023-10-13','Regular',0,43,'Male','Nagpur'),
(266,'Nisha Pillai','nisha.pillai266@gmail.com','2024-05-04','Premium',0,31,'Female','Kochi'),
(267,'Rohan Arora','rohan.arora267@gmail.com','2025-01-10','Regular',0,26,'Male','Indore'),
(268,'Meera Kulkarni','meera.kulkarni268@gmail.com','2023-11-29','Premium',0,52,'Female','Pune'),
(269,'Siddharth Jain','siddharth.jain269@gmail.com','2024-03-06','Regular',0,37,'Male','Delhi'),
(270,'Aditi Chawla','aditi.chawla270@gmail.com','2025-07-01','Premium',0,33,'Female','Mumbai'),
(271,'Rahul Sinha','rahul.sinha271@gmail.com','2024-08-19','Regular',0,42,'Male','Patna'),
(272,'Sneha Ghosh','sneha.ghosh272@gmail.com','2025-02-03','Premium',0,29,'Female','Kolkata'),
(273,'Harsh Vora','harsh.vora273@gmail.com','2023-09-22','Regular',0,48,'Male','Ahmedabad'),
(274,'Pooja Menon','pooja.menon274@gmail.com','2024-12-18','Premium',0,35,'Female','Chennai'),
(275,'Manav Gupta','manav.gupta275@gmail.com','2025-04-28','Regular',0,27,'Male','Delhi'),
(276,'Anjali Reddy','anjali.reddy276@gmail.com','2023-07-16','Premium',0,46,'Female','Hyderabad'),
(277,'Karan Oberoi','karan.oberoi277@gmail.com','2024-02-09','Regular',0,40,'Male','Noida'),
(278,'Priya Anand','priya.anand278@gmail.com','2025-03-30','Premium',0,31,'Female','Bengaluru'),
(279,'Neil Thomas','neil.thomas279@gmail.com','2023-10-25','Regular',0,53,'Male','Kochi'),
(280,'Tanya Sethi','tanya.sethi280@gmail.com','2024-11-14','Premium',0,28,'Female','Delhi'),
(281,'Aman Yadav','aman.yadav281@gmail.com','2025-05-12','Regular',0,38,'Male','Kanpur'),
(282,'Shreya Bose','shreya.bose282@gmail.com','2024-01-18','Premium',0,34,'Female','Kolkata'),
(283,'Ritesh Kulkarni','ritesh.kulkarni283@gmail.com','2023-08-30','Regular',0,49,'Male','Pune'),
(284,'Neha Arora','neha.arora284@gmail.com','2025-06-09','Premium',0,26,'Female','Delhi'),
(285,'Vikram Chauhan','vikram.chauhan285@gmail.com','2024-04-26','Regular',0,44,'Male','Jaipur'),
(286,'Sonal Patel','sonal.patel286@gmail.com','2025-01-15','Premium',0,30,'Female','Ahmedabad'),
(287,'Raghav Nanda','raghav.nanda287@gmail.com','2023-09-05','Regular',0,41,'Male','Mumbai'),
(288,'Kavya Iyer','kavya.iyer288@gmail.com','2024-06-30','Premium',0,36,'Female','Chennai'),
(289,'Aakash Mishra','aakash.mishra289@gmail.com','2025-03-08','Regular',0,33,'Male','Lucknow'),
(290,'Divya Verma','divya.verma290@gmail.com','2024-10-09','Premium',0,27,'Female','Delhi'),
(291,'Rohit Bhatia','rohit.bhatia291@gmail.com','2023-11-21','Regular',0,50,'Male','Chandigarh'),
(292,'Ira Sen','ira.sen292@gmail.com','2025-02-26','Premium',0,32,'Female','Kolkata'),
(293,'Nitin Purohit','nitin.purohit293@gmail.com','2024-08-01','Regular',0,45,'Male','Udaipur'),
(294,'Tanvi Joshi','tanvi.joshi294@gmail.com','2025-04-20','Premium',0,29,'Female','Pune'),
(295,'Abhishek Roy','abhishek.roy295@gmail.com','2023-10-11','Regular',0,39,'Male','Kolkata'),
(296,'Mitali Das','mitali.das296@gmail.com','2024-07-24','Premium',0,35,'Female','Bhubaneswar'),
(297,'Varun Saxena','varun.saxena297@gmail.com','2025-05-27','Regular',0,42,'Male','Delhi'),
(298,'Nandini Kapoor','nandini.kapoor298@gmail.com','2024-03-12','Premium',0,31,'Female','Mumbai'),
(299,'Parth Trivedi','parth.trivedi299@gmail.com','2023-12-28','Regular',0,47,'Male','Ahmedabad'),
(300,'Aisha Mirza','aisha.mirza300@gmail.com','2025-06-22','Premium',0,25,'Female','Hyderabad');

DESCRIBE feedback;        

INSERT INTO Transactions (customer_id, date, amount, product) VALUES

-- Customer 251 (Loyal)
(251,'2025-02-20',4200.00,'Smartphone'),
(251,'2025-04-15',1800.00,'Headphones'),
(251,'2025-06-18',950.00,'Power Bank'),
(251,'2026-01-12',3200.00,'Smart Watch'),

-- Customer 252 (Average)
(252,'2024-11-15',850.00,'Backpack'),
(252,'2025-03-11',1400.00,'Shoes'),
(252,'2025-10-05',700.00,'Wireless Mouse'),

-- Customer 253 (Loyal)
(253,'2023-10-02',6200.00,'Laptop'),
(253,'2024-05-18',2600.00,'Keyboard'),
(253,'2025-01-25',4500.00,'Monitor'),
(253,'2026-03-17',1800.00,'Headphones'),

-- Customer 254 (Average)
(254,'2025-04-08',650.00,'Bottle'),
(254,'2025-08-21',1200.00,'Shoes'),

-- Customer 255 (High Value)
(255,'2024-06-20',8500.00,'Laptop'),
(255,'2024-11-10',4300.00,'Tablet'),
(255,'2025-09-14',2900.00,'Smart Watch'),
(255,'2026-04-28',1600.00,'Headphones'),

-- Customer 256 (Average)
(256,'2025-02-01',980.00,'Power Bank'),
(256,'2025-07-22',1500.00,'Headphones'),
(256,'2026-01-30',1100.00,'Keyboard'),

-- Customer 257 (Loyal)
(257,'2023-09-12',5200.00,'Tablet'),
(257,'2024-06-14',1800.00,'Printer'),
(257,'2025-05-19',3500.00,'Monitor'),
(257,'2026-05-07',900.00,'Mouse'),

-- Customer 258 (Medium)
(258,'2024-08-01',900.00,'Shoes'),
(258,'2025-03-17',1500.00,'Backpack'),

-- Customer 259 (Premium)
(259,'2025-03-28',7800.00,'Smartphone'),
(259,'2025-08-11',2600.00,'Earbuds'),
(259,'2026-02-09',4200.00,'Camera'),

-- Customer 260 (Average)
(260,'2024-11-04',1250.00,'Office Chair'),
(260,'2025-09-22',2400.00,'Coffee Maker'),
(260,'2026-04-16',900.00,'Power Bank');


INSERT INTO Transactions (customer_id, date, amount, product) VALUES

-- Customer 261
(261,'2025-05-20',950.00,'Wireless Mouse'),
(261,'2025-08-14',1800.00,'Keyboard'),
(261,'2026-03-11',2400.00,'Office Chair'),

-- Customer 262
(262,'2023-12-18',6800.00,'Laptop'),
(262,'2024-05-21',2600.00,'Printer'),
(262,'2025-02-09',3400.00,'Monitor'),
(262,'2026-01-30',1500.00,'Headphones'),

-- Customer 263
(263,'2024-10-05',1100.00,'Shoes'),
(263,'2025-06-15',1700.00,'Backpack'),

-- Customer 264
(264,'2025-06-28',7900.00,'Smartphone'),
(264,'2025-09-18',2900.00,'Tablet'),
(264,'2026-05-10',2100.00,'Headphones'),

-- Customer 265
(265,'2023-11-02',700.00,'Bottle'),
(265,'2024-07-16',1200.00,'Shoes'),

-- Customer 266
(266,'2024-05-12',4200.00,'Smart Watch'),
(266,'2025-01-08',1700.00,'Power Bank'),
(266,'2026-02-20',2600.00,'Printer'),

-- Customer 267
(267,'2025-02-18',850.00,'Keyboard'),
(267,'2025-10-27',1350.00,'Headphones'),

-- Customer 268
(268,'2023-12-22',9100.00,'Laptop'),
(268,'2024-08-11',4500.00,'Monitor'),
(268,'2025-06-01',3300.00,'Camera'),
(268,'2026-04-14',1900.00,'Smart Watch'),

-- Customer 269
(269,'2024-03-18',1400.00,'Coffee Maker'),
(269,'2025-05-23',2300.00,'Office Chair'),
(269,'2026-01-15',900.00,'Mouse'),

-- Customer 270
(270,'2025-07-15',6200.00,'Tablet'),
(270,'2025-11-04',2800.00,'Headphones'),
(270,'2026-06-01',1500.00,'Keyboard'),

-- Customer 271
(271,'2024-09-04',650.00,'Bottle'),
(271,'2025-03-12',1100.00,'Shoes'),

-- Customer 272
(272,'2025-02-19',5400.00,'Smartphone'),
(272,'2025-08-30',2300.00,'Power Bank'),
(272,'2026-05-18',3700.00,'Monitor'),

-- Customer 273
(273,'2023-10-03',900.00,'Backpack'),
(273,'2024-11-20',1600.00,'Shoes'),
(273,'2025-07-27',2200.00,'Coffee Maker'),

-- Customer 274
(274,'2024-12-28',7300.00,'Laptop'),
(274,'2025-04-16',1800.00,'Printer'),
(274,'2026-03-22',3200.00,'Camera'),

-- Customer 275
(275,'2025-05-08',800.00,'Wireless Mouse'),
(275,'2025-12-12',1400.00,'Keyboard'),

-- Customer 276
(276,'2023-08-10',8100.00,'Laptop'),
(276,'2024-04-19',3500.00,'Monitor'),
(276,'2025-09-08',2700.00,'Smart Watch'),
(276,'2026-06-04',1600.00,'Headphones'),

-- Customer 277
(277,'2024-02-22',1200.00,'Backpack'),
(277,'2025-01-18',900.00,'Bottle'),

-- Customer 278
(278,'2025-04-09',6500.00,'Smartphone'),
(278,'2025-10-01',2400.00,'Printer'),
(278,'2026-05-24',3100.00,'Camera'),

-- Customer 279
(279,'2023-11-16',850.00,'Shoes'),
(279,'2024-09-21',1700.00,'Office Chair'),
(279,'2025-12-09',1200.00,'Keyboard'),

-- Customer 280
(280,'2024-12-02',6900.00,'Tablet'),
(280,'2025-08-17',2200.00,'Headphones'),
(280,'2026-04-28',4100.00,'Monitor');


INSERT INTO Transactions (customer_id, date, amount, product) VALUES

-- Customer 281
(281,'2025-06-02',950.00,'Keyboard'),
(281,'2025-11-18',1800.00,'Office Chair'),
(281,'2026-04-06',2700.00,'Printer'),

-- Customer 282
(282,'2024-02-11',7200.00,'Laptop'),
(282,'2024-09-27',2500.00,'Monitor'),
(282,'2025-05-30',3200.00,'Camera'),
(282,'2026-03-10',1700.00,'Headphones'),

-- Customer 283
(283,'2023-09-19',800.00,'Bottle'),
(283,'2024-10-06',1400.00,'Shoes'),

-- Customer 284
(284,'2025-06-22',6800.00,'Smartphone'),
(284,'2025-10-14',2300.00,'Power Bank'),
(284,'2026-05-05',3600.00,'Tablet'),

-- Customer 285
(285,'2024-05-01',1100.00,'Backpack'),
(285,'2025-02-18',1700.00,'Keyboard'),
(285,'2026-01-12',900.00,'Wireless Mouse'),

-- Customer 286
(286,'2025-01-28',5300.00,'Smart Watch'),
(286,'2025-08-25',2800.00,'Printer'),
(286,'2026-04-20',1900.00,'Headphones'),

-- Customer 287
(287,'2023-10-14',650.00,'Bottle'),
(287,'2024-08-19',950.00,'Shoes'),

-- Customer 288
(288,'2024-07-12',7900.00,'Laptop'),
(288,'2025-03-16',4200.00,'Monitor'),
(288,'2025-12-08',3100.00,'Camera'),
(288,'2026-06-02',1500.00,'Power Bank'),

-- Customer 289
(289,'2025-04-15',1200.00,'Office Chair'),
(289,'2025-09-20',1600.00,'Keyboard'),

-- Customer 290
(290,'2024-11-21',6500.00,'Tablet'),
(290,'2025-06-28',2400.00,'Printer'),
(290,'2026-05-14',3300.00,'Smart Watch'),

-- Customer 291
(291,'2023-12-05',700.00,'Bottle'),
(291,'2024-07-29',1200.00,'Backpack'),

-- Customer 292
(292,'2025-03-11',6100.00,'Smartphone'),
(292,'2025-08-09',2600.00,'Headphones'),
(292,'2026-04-30',4100.00,'Monitor'),

-- Customer 293
(293,'2024-08-15',1000.00,'Keyboard'),
(293,'2025-04-27',1700.00,'Coffee Maker'),
(293,'2026-02-18',2200.00,'Office Chair'),

-- Customer 294
(294,'2025-05-04',7600.00,'Laptop'),
(294,'2025-11-09',2500.00,'Camera'),
(294,'2026-06-10',1800.00,'Printer'),

-- Customer 295
(295,'2023-11-18',900.00,'Shoes'),
(295,'2025-01-22',1300.00,'Backpack'),

-- Customer 296
(296,'2024-08-30',5700.00,'Tablet'),
(296,'2025-07-12',2100.00,'Power Bank'),
(296,'2026-03-29',2800.00,'Monitor'),

-- Customer 297
(297,'2025-06-18',850.00,'Wireless Mouse'),
(297,'2025-12-16',1400.00,'Keyboard'),

-- Customer 298
(298,'2024-04-20',8400.00,'Laptop'),
(298,'2025-01-10',3900.00,'Monitor'),
(298,'2025-10-23',2600.00,'Camera'),
(298,'2026-05-21',1900.00,'Headphones'),

-- Customer 299
(299,'2024-01-15',950.00,'Shoes'),
(299,'2025-05-09',1600.00,'Backpack'),
(299,'2026-03-17',2100.00,'Office Chair'),

-- Customer 300
(300,'2025-07-02',7200.00,'Smartphone'),
(300,'2025-11-28',3100.00,'Tablet'),
(300,'2026-06-18',2500.00,'Smart Watch');


INSERT INTO Feedback (customer_id, date, rating, comments, sentiment) VALUES

-- Customer 251
(251,'2025-03-01',5,'Excellent service and fast delivery.','Positive'),
(251,'2025-07-01',5,'Very happy with the product quality.','Positive'),

-- Customer 252
(252,'2024-12-05',4,'Good experience overall.','Positive'),

-- Customer 253
(253,'2024-01-12',5,'Excellent laptop quality.','Positive'),
(253,'2025-06-15',4,'Satisfied with customer support.','Positive'),

-- Customer 254
(254,'2025-05-11',3,'Product quality is average.','Neutral'),

-- Customer 255
(255,'2024-07-10',5,'Premium quality products.','Positive'),
(255,'2025-10-15',5,'Will definitely purchase again.','Positive'),

-- Customer 256
(256,'2025-02-05',3,'Delivery was average.','Neutral'),

-- Customer 257
(257,'2024-01-18',5,'Very satisfied with the service.','Positive'),
(257,'2025-06-01',5,'Highly recommended.','Positive'),

-- Customer 258
(258,'2024-08-20',2,'Delivery was delayed and support was slow.','Negative'),

-- Customer 259
(259,'2025-04-05',5,'Amazing shopping experience.','Positive'),
(259,'2026-02-15',4,'Product matched expectations.','Positive'),

-- Customer 260
(260,'2024-12-01',3,'Average service and packaging.','Neutral'),

-- Customer 261
(261,'2025-06-10',3,'Could be improved.','Neutral'),

-- Customer 262
(262,'2024-02-15',5,'Fantastic product quality.','Positive'),
(262,'2025-08-10',5,'Very satisfied with my purchase.','Positive'),

-- Customer 263
(263,'2024-11-01',2,'Packaging was poor.','Negative'),

-- Customer 264
(264,'2025-07-10',5,'Loved the smartphone.','Positive'),
(264,'2026-01-10',4,'Very good experience.','Positive'),

-- Customer 265
(265,'2024-08-01',1,'Very disappointed with the purchase.','Negative'),

-- Customer 266
(266,'2024-06-01',5,'Fast delivery and excellent support.','Positive'),
(266,'2026-03-05',4,'Good customer support.','Positive'),

-- Customer 267
(267,'2025-03-01',3,'Average quality product.','Neutral'),

-- Customer 268
(268,'2024-01-15',5,'Outstanding service.','Positive'),
(268,'2025-08-20',5,'Excellent products and quick delivery.','Positive'),

-- Customer 269
(269,'2025-05-30',2,'Not worth the price.','Negative'),

-- Customer 270
(270,'2025-08-01',4,'Very nice shopping experience.','Positive');


INSERT INTO Feedback (customer_id, date, rating, comments, sentiment) VALUES

-- Customer 271
(271,'2024-09-10',2,'Delivery was slower than expected.','Negative'),

-- Customer 272
(272,'2025-03-05',5,'Excellent product and fast delivery.','Positive'),
(272,'2025-10-12',4,'Very satisfied with the overall service.','Positive'),

-- Customer 273
(273,'2023-10-15',3,'Product quality is acceptable.','Neutral'),
(273,'2025-08-01',2,'Customer support could be better.','Negative'),

-- Customer 274
(274,'2025-01-08',5,'Amazing laptop, worth every penny.','Positive'),
(274,'2026-03-30',5,'Excellent shopping experience.','Positive'),

-- Customer 275
(275,'2025-06-10',3,'Average quality for the price.','Neutral'),

-- Customer 276
(276,'2023-09-05',5,'Fantastic premium products.','Positive'),
(276,'2024-12-15',5,'Very happy with every purchase.','Positive'),
(276,'2026-06-12',4,'Reliable customer support.','Positive'),

-- Customer 277
(277,'2024-03-05',1,'Very poor experience.','Negative'),

-- Customer 278
(278,'2025-05-20',5,'Loved the smartphone quality.','Positive'),
(278,'2026-01-18',4,'Fast delivery and nice packaging.','Positive'),

-- Customer 279
(279,'2024-10-05',2,'Product arrived damaged.','Negative'),

-- Customer 280
(280,'2025-01-12',5,'Tablet performance is excellent.','Positive'),
(280,'2026-05-15',4,'Very satisfied overall.','Positive'),

-- Customer 281
(281,'2025-07-05',3,'Good product but delivery was average.','Neutral'),

-- Customer 282
(282,'2024-03-10',5,'Laptop quality exceeded expectations.','Positive'),
(282,'2025-09-18',5,'Outstanding service.','Positive'),

-- Customer 283
(283,'2024-11-15',1,'Poor quality product.','Negative'),

-- Customer 284
(284,'2025-07-10',5,'Excellent smartphone and fast shipping.','Positive'),
(284,'2026-05-20',4,'Very good customer support.','Positive'),

-- Customer 285
(285,'2025-03-05',3,'Average shopping experience.','Neutral'),

-- Customer 286
(286,'2025-02-10',5,'Very satisfied with the smartwatch.','Positive'),
(286,'2026-04-25',4,'Good quality accessories.','Positive'),

-- Customer 287
(287,'2024-09-02',1,'Not satisfied with the product.','Negative'),

-- Customer 288
(288,'2024-08-15',5,'Excellent laptop performance.','Positive'),
(288,'2025-12-15',5,'Will definitely recommend this store.','Positive'),

-- Customer 289
(289,'2025-05-01',3,'Product is okay but packaging needs improvement.','Neutral'),

-- Customer 290
(290,'2025-01-05',5,'Very happy with the tablet.','Positive'),
(290,'2026-05-25',4,'Good purchase experience.','Positive'),

-- Customer 291
(291,'2024-01-20',2,'Support team was unhelpful.','Negative'),

-- Customer 292
(292,'2025-04-02',5,'Amazing experience from start to finish.','Positive'),
(292,'2026-05-05',5,'Excellent quality and quick delivery.','Positive'),

-- Customer 293
(293,'2024-09-20',3,'Decent experience overall.','Neutral'),

-- Customer 294
(294,'2025-06-01',5,'Fantastic laptop and excellent support.','Positive'),
(294,'2026-06-15',4,'Very pleased with the service.','Positive'),

-- Customer 295
(295,'2025-02-01',1,'Worst purchase I have made.','Negative'),

-- Customer 296
(296,'2025-08-01',4,'Very good tablet and accessories.','Positive'),

-- Customer 297
(297,'2025-07-01',2,'Delivery delay was disappointing.','Negative'),

-- Customer 298
(298,'2024-05-01',5,'Premium quality products.','Positive'),
(298,'2026-05-25',5,'Excellent customer experience.','Positive'),

-- Customer 299
(299,'2025-06-01',3,'Average experience, nothing special.','Neutral'),

-- Customer 300
(300,'2025-08-10',5,'Excellent products and outstanding service.','Positive'),
(300,'2026-06-25',5,'Will definitely shop again.','Positive');

SELECT * FROM customer_ml_view;
WHERE customer_id BETWEEN 1 AND 250;

UPDATE Customers
SET churned = 1
WHERE customer_id IN (
254,258,261,263,265,267,269,273,275,277,
279,283,285,287,289,291,293,295,297,299
);

UPDATE Customers
SET location = 'Ahmedabad'
WHERE customer_id >= 251
  AND location = 'Surat';
  
  SELECT DISTINCT location
FROM Customers
ORDER BY location;

UPDATE Customers
SET location = 'Ahmedabad'
WHERE location = 'Surat';

UPDATE Customers
SET location = CASE
    WHEN location = 'Kolkata' THEN 'Delhi'
    WHEN location = 'Kochi' THEN 'Chennai'
    WHEN location = 'Surat' THEN 'Ahmedabad'
    WHEN location = 'Noida' THEN 'Delhi'
    WHEN location = 'Jaipur' THEN 'Delhi'
    WHEN location = 'Indore' THEN 'Ahmedabad'
    WHEN location = 'Nagpur' THEN 'Mumbai'
    WHEN location = 'Lucknow' THEN 'Delhi'
    WHEN location = 'Kanpur' THEN 'Delhi'
    WHEN location = 'Patna' THEN 'Kolkata'
    WHEN location = 'Udaipur' THEN 'Ahmedabad'
    WHEN location = 'Bhubaneswar' THEN 'Kolkata'
    WHEN location = 'Chandigarh' THEN 'Delhi'
    ELSE location
END;
SET SQL_SAFE_UPDATES = 0;

SELECT COUNT(*) FROM customer_ml_view;
SELECT COUNT(*) FROM Retention_Alerts;
SELECT customer_id, COUNT(*) AS total_predictions
FROM Retention_Alerts
GROUP BY customer_id
HAVING COUNT(*) > 1;

DELETE FROM Retention_Alerts;
SELECT COUNT(*) FROM Retention_Alerts;

SELECT COUNT(*)
FROM Customers
WHERE churned = 0;

describe users;
 SELECT username,email FROM Admin WHERE username=6;
 
 DESCRIBE transactions;
 DESCRIBE customers;