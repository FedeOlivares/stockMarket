Welcome to StockMarketLite

This web app will allow you to Quote, Buy and Sell stocks on the open market
While the Buy and sell options are not real and the money is not real either
the prices are real with current prices based on the Yahoo Finance API. 

While the Front-End looks simple, Its more than enough as this was more of an effort
in API integration and database use (MySQL).
All passwords are protected to the best current standards and the site is protected 
against SQL injections, selling and buying are server side so no dev tools manipulation 
can induce a buy or sell option if unavailable. Likewise your bankroll (cash or total
value of the stock) is calculated and stored server-side. 

I hope you enjoy it.
It can be forked and run locally with "python flask -m run" command.