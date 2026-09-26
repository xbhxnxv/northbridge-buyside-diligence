# Interview prep

Five questions I am most likely to be asked about this project, with answers to say out loud (about 60 to 90 seconds each) and two follow-ups each. Every figure is from the pipeline. The project is a self-directed simulation on synthetic data.

## 1. How did you reconcile the data, and what did you do with differences you couldn't explain?

I rebuilt revenue from the invoice ledger, customer by product by month, and compared it with the management accounts every month, at total and at product-line level. Before that I cleaned out 40 exact duplicate invoices worth £96,957. There were also 15 negative amounts on invoices marked paid, and I tested three treatments for those against the management accounts. Only excluding them tied every month, so management had left them out. With that, the ledger tied to the product lines in all 48 months. The reported total still differed in four months, by round amounts: reported 2025 revenue was £15,000 higher than the invoices support. I couldn't explain those from the data, so I labelled them unexplained, quantified them by year, and put specific questions in the Q&A log: the journals, who posted them, and which figure is in the information memorandum. I flagged any month with a difference above £1,000 and treated anything above 0.5% of a month's revenue as material.

- *Why not just adjust the total to match the lines?* Because that would be me deciding which number is right without evidence. The cube is unaffected either way; the question goes to management.
- *How would the other side's adviser attack this?* They'd say the differences are immaterial. They are, at under 0.1% of any year. But manual entries to reported revenue are a controls point, and the buyer should know which figure it is paying on.

## 2. How did you define NRR and GRR, and what are their limits here?

NRR is December MRR from the customers who were active the previous December, divided by their MRR that previous December. Churned customers count at zero and new customers are left out. GRR is the same, but each customer's closing MRR is capped at its opening MRR, so it shows only losses. MRR is recurring billings before credit notes, because credit notes are one-off concessions and would make a customer look as if it had churned. NRR was 95.8%, 98.7% and 95.4% for 2023 to 2025, and GRR fell from 94.5% to 88.8%. There are two limits. The data starts in January 2022, so there's no December 2021 and no 2022 figure. And every line had a 5% price increase in 2024 and 7% in 2025, which lifts NRR without any change in behaviour. Taking the price out, 2025 NRR was 89.2%.

- *Why does the price increase barely move GRR?* GRR caps each customer at its opening MRR, so a price rise can't push a customer above 100%; it only offsets some downgrades.
- *What would you want from management?* Confirmation of the price increases and their contract basis (Q15), and churn reasons by customer.

## 3. What was the biggest red flag, and what does it mean for price or structure?

The biggest one is the £4.08m of implementation revenue billed in 2025. Every other implementation invoice in the data is billed in the month a new customer signs up, with a median of £3,180. These 45 were all to existing customers, none in their signup month, much larger, and all in the year before the sale. They take 2025 growth from 11.9% to 22.8%. They also came with delivery cost, which is why gross margin fell 4.0 points. On price, I'd value the business on recurring revenue or ARR and treat that £4.08m as non-recurring until we see contracts and acceptance. On structure, a specific warranty and indemnity on those contracts. And because ARR growth before price was only 3.1%, an earn-out tied to ARR or NRR protects the buyer if the growth story doesn't hold.

- *How did you find it?* An outlier screen by product, then comparing each implementation invoice's date with the customer's signup month, then the invoice ID sequence, which showed them as one block.
- *Could it be legitimate?* Yes: it could be real project work. That's why it goes to management as a question (Q02 onwards) and into the SPA as a warranty, and the data stays as it is.

## 4. Tell me about one judgement call you made in cleaning.

The customer names. Once I normalised legal forms, 229 pairs of customer IDs had the same name, differing only by Ltd against Limited. The easy thing would have been to merge them. I checked whether they looked like the same business: region, size, industry and account manager agreed no more often than for two random customers, and most pairs had contracts running at the same time. So I didn't merge anything. I flagged them and asked management whether any are the same legal entity. Merging on a guess would have changed customer counts, churn and concentration, which are exactly the numbers a buyer relies on.

- *What if management says some are the same?* Then I'd merge those specific pairs through a mapping table, rerun the pipeline and show the effect on churn and concentration.
- *Another judgement you made?* Keeping the £4.08m of implementation revenue in the cube with a flag. Whether it counts is a revenue-quality judgement, so I made it in the analysis and the memo and left the cleaning step to fix data errors only.

## 5. What would you do differently with real client data?

First, I'd get the general ledger and bank data so I could tie the invoices to cash as well as to the management accounts. Cash is the stronger test of whether revenue is real. Second, contracts for the largest customers, so ARR can be checked against contracted terms. Third, I'd agree definitions with the deal team before building, because NRR, churn and ARR mean slightly different things at different firms. On the build, the pipeline would run in the client's environment, for example Snowflake or Alteryx; I wrote an Alteryx version of the preparation steps with check totals for that reason. And I'd have a manager review the cleaning log before anything went to the client.

- *What would you automate first?* The reconciliation and its checks, because they rerun every time the data room is refreshed.
- *What was hardest?* Keeping every number in the databook, memo and README tied to one source. I solved it by generating them from the same output tables and testing the figures.
