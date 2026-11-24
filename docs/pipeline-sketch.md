# Sketch: sales for each store and day

Consumer: the owner's morning sheet. Question: how many units and how many dollars did each store sell each day?
Sources: the sales API (order lines) and two files, `products.csv` and `stores.csv`.

| # | Step | Layer | ETL or ELT |
|---|------|-------|------------|
| 1 | Save every page of the API exactly as it arrives | raw | load first |
| 2 | Save `products.csv` and `stores.csv` exactly as they are | raw | load first |
| 3 | Give each column of the lines its type and a clear name | staging | ELT, in SQL |
| 4 | Do the same for the two files, one staged table for each file | staging | ELT, in SQL |
| 5 | Join lines to products (the price) and to stores (the name) | serving | ELT, in SQL |
| 6 | Add up units and dollars for each store and day | serving | ELT, in SQL |
| 7 | Publish the table `sales_by_store_day` for the sheet | serving | ELT, in SQL |

Batch or stream: batch, once a night, because the sheet is read once a morning.
