"""FactoryFlow AI — Deduction Coder.

An ERP-agnostic, interface-driven scaffold that automates *deduction coding*:
the process of taking a customer deduction (a short-payment on an invoice) and
splitting it across the correct accounting dimensions — Product Category x Sales
Channel, down to SKU — weighted by the sales-dollar value of what shipped, then
posting each coded split to the right GL account.

The pipeline has five obvious stages, each behind a small interface so adopters
can swap in their own systems:

    ingest  ->  parse  ->  resolve  ->  allocate  ->  post

* ``ingest``   read an email inbox, pull out deduction backup attachments.
* ``parse``    turn each backup file (CSV/XLSX/PDF) into line items + a total.
* ``resolve``  look up the referenced invoice's shipped lines from the ERP.
* ``allocate`` split the deduction across Category x Channel x SKU.
* ``post``     write each coded split to the accounting system's GL.

Everything shipped here runs on **synthetic data only**. See DISCLAIMER.md.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
