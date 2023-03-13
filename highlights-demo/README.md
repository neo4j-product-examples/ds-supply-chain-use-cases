# Supply Chain and Logistics Highlights Demo

## Outline
1. Staging Steps
2. Explore/Bloom Analysis with Graph Data Science
3. Supply Chain Analytics with Graph Data Science & Python
4. Finding and Recommending Optimal Routes 
5. ...and more

## Staging Steps
1. __Configure DB Credentials__: Create a copy of the `db-credentials.env.template` file and name it `db-credentials.env`. Fill in uri, username, and password credentials for your Neo4j database. set `AURA_DS` to true or false as appropriate.
2. __Load the Data__: Two options:
   1. __Load the data using `transform-and-load.ipynb` (recommended)__: The notebook automatically pulls source data from an external website.  It takes a few minutes to complete depending on your internet connection.
   2. __Load from dump file__: A Neo4j 5 dump file with the data is located [here](https://drive.google.com/drive/folders/1bw9AZGejNJm6875yExMaf4uOtPPq2Crd)
3. __Import and use Bloom Perspective__: `bloom-perspective.json`