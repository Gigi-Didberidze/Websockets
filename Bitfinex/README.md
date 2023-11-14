# Bitfinex Websocket Instructions
This file includes the explanation of app.py outputs
## Collecting Trade Data
te --> trade executed  
tu --> trade execution update  

Response format (trading pairs)
```
[
  CHANNEL_ID,
  <"te", "tu">,
  [
    ID,
    MTS,
    AMOUNT,
    PRICE
  ]
]
```

### Request Fields
| Fields      | Type        | Description                     |
| ----------- | ----------- | ------------------------------- |
| SYMBOL      | String      | Trading pair or funding currency|

### Stream Fields

| Fields      | Type        | Description                     |
| ----------- | ----------- | ------------------------------- |
| CHANNEL_ID  | int         | Identification number assigned to the channel for the duration of this connection. |
| ID         | int       | Trade ID|
| MTS         | int       | millisecond time stamp      |
| ±AMOUNT  | float         | Amount bought (positive) or sold (negative). |
| PRICE    | float       | Price at which the trade was executed |

## Collecting Ticker Data
Respone format (trading pairs) 

```
[
    CHANNEL_ID,
    [  
        BID,  
        BID_SIZE,  
        ASK,  
        ASK_SIZE,  
        DAILY_CHANGE,  
        DAILY_CHANGE_RELATIVE,  
        LAST_PRICE,  
        VOLUME,  
        HIGH,  
        LOW  
  ]  
]
```
### Request Fields

| Fields      | Type        | Description                     |
| ----------- | ----------- | ------------------------------- |
| SYMBOL      | String      | Trading pair or funding currency|

### Stream Fields

| Fields      | Type        | Description                     |
| ----------- | ----------- | ------------------------------- |
| CHANNEL_ID  | int         | Identification number assigned to the channel for the duration of this connection. |
| FRR         | float       | Flash Return Rate - average of all fixed rate funding over the last hour (funding tickers only) |
| BID         | float       | Price of last highest bid       |
| BID_PERIOD  | int         | Bid period covered in days (funding tickers only) |
| BID_SIZE    | float       | Sum of the 25 highest bid sizes |
| ASK         | float       | Price of last lowest ask        |
| ASK_PERIOD  | int         | Ask period covered in days (funding tickers only) |
| ASK-SIZE    | float       | Sum of the 25 lowest ask sizes  |
| DAILY-CHANGE| float       | Amount that the last price has changed since yesterday |
| DAILY_CHANGE_RELATIVE| float      | 	Relative price change since yesterday (*100 for percentage change) |
| LAST_PRICE  | float       | Price of the last trade.        |
| VOLUME      | float       | Daily volume                    |
| HIGH        | float       | Daily high                      |
| LOW         | float       | Daily low                       |
| FRR_AMOUNT_AVAILABLE| float       | The amount of funding that is available at the Flash Return Rate (funding tickers only)|

## Collecting Order Book Data
Respone format (trading pairs) 

```
[
  CHANNEL_ID,
  [
    [
      PRICE,
      COUNT,
      AMOUNT
    ],
    ...
  ]
]
```


### Request Fields

| Fields      | Type        | Description                     |
| ----------- | ----------- | ------------------------------- |
| SYMBOL      | String      | Trading pair or funding currency|
| PRECISION      | String      | Level of price aggregation (P0, P1, P2, P3, P4). The default is P0|
| FREQUENCY      | String      | Frequency of updates (F0, F1). F0=realtime / F1=2sec. The default is F0.|
| LENGTH      | String      | Number of price points ("1", "25", "100", "250") [default="25"]|
| SUBID      | String      | Optional user-defined ID for the subscription|

### Stream Fields

| Fields      | Type        | Description                     |
| ----------- | ----------- | ------------------------------- |
| CHANNEL_ID  | int         | Identification number assigned to the channel for the duration of this connection. |
| PRICE         | float       | Price level|
| RATE         | float       | Rate level      |
| PERIOD	  | int         | Period level |
| COUNT    | int       | Number of orders at that price level (delete price level if count = 0) |
| ±AMOUNT	    | float       | Total amount available at that price level. Trading: if AMOUNT > 0 then bid else ask; Funding: if AMOUNT < 0 then bid else ask;|

## Algorithm to create and keep a trading book instance updated

1. subscribe to channel
2. receive the book snapshot and create your in-memory book structure
3. when count > 0 then you have to add or update the price level  
3.1   if amount > 0 then add/update bids  
3.2 if amount < 0 then add/update asks  
4. when count = 0 then you have to delete the price level.  
4.1 if amount = 1 then remove from bids  
4.2 if amount = -1 then remove from asks  
## Algorithm to create and keep a funding book instance updated

1. subscribe to channel
2. receive the book snapshot and create your in-memory book structure
3. when count > 0 then you have to add or update the price level  
3.1 if amount > 0 then add/update asks (offers)  
3.2 if amount < 0 then add/update bids  
4. when count = 0 then you have to delete the price level.  
4.1 if amount = 1 then remove from asks (offers)  
4.2 if amount = -1 then remove from bids  

### Node.JS example gists:

Aggregated Book: https://gist.github.com/prdn/b8c067c758aab7fa3bf715101086b47c  
Raw Book: https://gist.github.com/prdn/b9c9c24fb1bb38604dcd1e94ee89dd9e