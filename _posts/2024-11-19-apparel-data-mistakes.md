---
title: "The 5 Data Mistakes Every Apparel Company Makes"
date: 2024-11-19T00:00:00
description: In this article, we discuss the 5 data mistakes that every Apparel company makes, provide some context as to why, and discuss ways to solve them.
header:
  image: /assets/images/data_mistakes.png
categories:
  - data management
tags:
  - data
# cSpell:ignore Womens ABAP
---

Over the course of 15 years, I have had the pleasure of working at and partnering with some amazing companies in the Apparel space. While I am not qualified to design product, I've been fortunate to work with many of the different business areas that make up an Apparel organization. As a data practitioner, this has immensely helpful when thinking about crafting data strategies that work for the entire organization.

Interestingly, I found that the companies I worked at repeated the same data mistakes over and over again. In this article, I highlight five major mistakes to avoid; doing so will pay immense dividends in terms of how much your organization has to spend to manage data, and in turn how effectively your organization can use data.

# PLM System Overreach

The first major mistake I see Apparel companies make is to try and solve all of their product management issues with a PLM system.

Companies have a real need to categorize products, plan, merchandise, and manage changes throughout the product's lifecycle. While in theory a PLM system could help you manage all of these, in practice I think PLM systems become far less useful the further downstream you get from managing the technical aspects of a product.

For example, I've seen companies try to implement planning solutions inside of their PLM. The logic that leads you to this solution usually goes:

  1. We have a lot of plans that we manage in Excel. We need to store them somewhere else
  2. We do a lot of data entry into our PLM system already
  3. Product line managers might want to know how well a product is planned to craft their line

Sure, this is all well intentioned, but assuming your company has gone down this path, the question you must ask yourself after putting planning data into your PLM is *now what?*. I've yet to come across a PLM system that offers any type of robust planning solution (ironically, Excel has more to offer). By going down this path, your company has done nothing but "shuffle sand." It may feel good that you got your data into a "real system," but that system offers no capabilities to augment the existence of that data, and you've actually created more busy work for people to store, transmit, and analyze plans.

Another common culprit for abuse of the PLM system is Master Data Management (MDM). Once again, there's some pretty logical thinking that deceives you into thinking your PLM system is the right place to try and manage this. Here's the reasoning:

  1. To achieve good MDM, we need to fix problems at the source
  2. Our product line is developed in the PLM system
  3. Product line managers should own the quality of their data

There are at least two major issues with this logic. First, the odds that your PLM system will completely encompass your product line offering are low. In the direct-to-consumer line of business, it is common to partner with 3rd parties on licensing agreements that allow you to cross-sell products. If you try to build these 3rd party products into your PLM system, you'll likely violate all of the assumptions your system has in place about how products should be managed. Although very few PLM implementations actually enforce automated rules, just these few extra styles will weaken the overall way that you use your PLM to manage products that your company actually designs.

The other main issue is that product line managers often do not have complete control over their product. Sure, they manage a lot, but teams downstream from them almost assuredly will have their own custom product categorizations. To illustrate, let's assume that your supply planning team wants to codify how a product should be stocked. If your goal is to have this information in your PLM system, then either your supply planning teams or product line management teams have to enter it somehow.

In the case that your supply planning teammates maintain this data, you'd have to train them up on a system to leverage only a very small portion of it. This is a waste of your supply planning teams' time, and many PLM systems have per-user licensing agreements that make this unnecessarily expensive. If, on the other hand, you ask the product line manager to maintain this, your data quality and maintenance are surely going to suffer. You've asked your product line manager to own data that has nothing to do with their core function, which is a recipe for disaster.

# ERP System Overreach

Now that we've cast some doubts on the flexibility offered by PLM systems, let's move our focus onto the next biggest systems culprit - the ERP system.

Towards the beginning part of this millennium, the concept of partnering with an ERP system provider was strongly rooted at many Apparel companies. Not only did ERP providers want to help you manage and track inventory, they wanted to sell you a reporting platform and anything under the sun that your IT organization wanted.

While still strongly rooted, I think this model has started to scale back in recent years. Instead of relying on the Oracle's and SAP's of the world for reporting solutions, many organizations have started investing in specialized reporting platform providers like Snowflake and Databricks to handle their data needs. Others may be perfectly content to build their own reporting solution, using a variety of cloud-based offerings and open source tools that have come into vogue within the past 10 years.

However, old habits die hard, and there is a large consulting business within the Apparel space that will still push you towards leveraging ERP systems and the tools that their providers offer for any customizations. ERP systems are inherently inflexible, and their paired reporting solutions are extremely subpar. If you go this route, you are going to use proprietary, poorly understood ERP-provided tools (does anyone still write ABAP?!?). This will make the Oracle and SAP consultants of the world very happy (and rich!), but you'll continue along with an inflexible, non-specialized solution.

But what if you've seen the writing on the wall and avoided buying more than an ERP from ERP vendors for the past decade? Well done for being ahead of the curve, but you still need to be careful when customizing your ERP system to add more data than it is designed to manage.

I usually see this customization manifest itself through custom SQL scripts that modify the underlying database. In rarer cases, this has the downside of locking you into the database underlying your ERP. Unless you strictly write ANSI SQL, you've just added to your workload for upgrading or replacing your database.

Another issue is that ERP providers are very strict about what they support when it comes to customization. If you make a mistake and modify the wrong table or schema, you've opened yourself up to the possibility that the ERP provider will claim their expensive support agreement as having been violated.

Finally, it's worth noting that this is a pretty archaic way of managing systems. There are very few other modern day applications where database-level customization is considered a best practice; more commonly, you'd have some type of middleware that affords you safety and flexibility when augmenting your system. Directly modifying the underlying application database is so 90s.

To be clear, I don't want this section to read as saying that there is no value to ERP systems. Smaller organizations tend to forgo traditional ERP systems for SaaS solutions to manage production, shipping and inventory. These solutions work up to a certain extent, but they become very difficult to scale. Having a centralized ERP system alongside many standard integrations (vendor management portals, warehouse management modules, point-of-sale systems, etc...) can be of immense value to an organization.

However, you should keep in mind that the benefits of an ERP are mainly relevant to tracking and creating a transactional record of events. When it comes to data and analytics, open-source tooling has completely disrupted the field that ERP vendors tried to dominate in the early 2000s. Open-source tooling is better, and hiring associates with that skill-set is significantly easier. The odds of a young data professional coming out of college knowing how to use SAP or Oracle is pretty low, yet the odds of them knowing how to use tools like Python are high.

# Ceding Data to 3rd Parties

As a data professional, this one hurts to see. Once again, let's talk about the logical steps that get you to this point:

  1. Your marketing team uses a 3rd party tool that is great for <customer tracking, email marketing, etc...>
  2. The 3rd party tool promises you they can build you a "single view of the customer"
  3. You start copying all of your data to the third party tool, so you don't have to manage it yourself

There's a few issues with this. For starters, I've yet to come across a 3rd party SaaS provider that effectively manages an organization's data. Sure, they can likely produce some attractive reports on top of the data that they created, but they simply do not have the capabilities to cover your entire organization. Managing data quality, ensuring systems talk to one another in meaningful ways, and aligning systems with business processes is an insanely complex task. If you think your email marketing platform that you pay for on a subscription basis is going to solve that for you...well I've got some snake oil to sell you too!

If you go this route, you need to be aware that you are giving away one of the greatest assets that your organization has. Within the past decade, we've continued to see data become more valuable by the year. Whether you are using data for analytical purpose, or you are collecting data that one day may help you augment an AI model for your organization, *you* should own that.

Of course a 3rd party SaaS provider would love to take this from you. Storage is exceptionally cheap, and, save having some very low-level integration with your third party, the amount of data that you send to them is going to cost peanuts. This will make your finance team happy, but it won't take long to find that not only have you ceded control of your invaluable treasure chest of data, you've locked yourself into a 3rd party provider.

You should also consider that third party SaaS providers are being bought, sold, and acquired at a profound pace; any of these events can greatly change the priorities of that provider. Even large players like Google have had to make sweeping architectural changes to how they solution their products (Universal Analytics -> GA4, anyone?).

Your organization needs your data and they need it to be comprehensive, accurate, and insightful. Before you give your data away to 3rd parties, ask yourself if you truly think that they are going to forever architect a comprehensive solution for your organization, with limited interaction with your business and at the cost of a subscription. Odds are low, so that's a huge risk to take on.

# No Processes for Data Quality Control

This definitely falls under the purview of MDM, but is critical enough to report here as we talk about data in more general terms. Please DO NOT allow your teams to categorize their data differently across business units. This is short-term win for the business unit that feels like it needs more flexibility to manage its view of products and consumers, but you are proverbially "robbing Peter to pay Paul" when you do this.

This is a top-down failure within your data organization. Each analyst may be happy to have this freedom, but undoubtedly your data and communications will need to cross multiple parts of your organization. Can you imagine trying to cobble together a spreadsheet from three different business units that each refer to your product as:

  * Awesome Women's T
  * Awesome W's T
  * Awesome Womens T

As humans, we easily recognize these as the same thing. Computers are pretty stupid though (yes, even in the age of AI) so you've introduced work for someone somewhere to try and clean up this mess manually.

*What a huge waste of time*. I can't stress this enough. Your poor data quality analyst is going to have to go through, reclassify these, communicate with people to try and establish a best practice, update a multitude of Excel files, etc...all to ultimately produce a non-reproducible report that leaves some ambiguity as to how well this product is being managed.

You may have less control over this on the consumer side and have to pay third party services to help cleanse your data (addresses come to mind), but those services tend to be relatively affordable. On the product side, setting standards up front and measuring adherence to those standards is something you can do up front. Please do this and save your organization from all of the non-value added data cleansing activities downstream.

# Undervaluing Manufacturing Data

Very few large brands in Apparel do their own manufacturing at scale. Historically, large brands in the U.S. have partnered with overseas factories to produce goods at very low prices. As the world has changed and the geo-political climate evolves, it is hard to say how the future of this will shape out, but I sincerely doubt that there will be a radical, overnight shift to this setup.

With that being the case, manufacturing partners are rarely ever managed within a comprehensive data platform. At a minimum, I've seen Excel be the system of choice to transmit data from the manufacturing company to the Apparel brand. If you wanted to get fancy, you might have a quality control system and an ERP integration with your manufacturer, but these aren't typically technologically savvy integrations.

Is that the best we can do with manufacturing data? Of course not! Think about the potential for automation - wouldn't it be cool to have more AI trained to automate tasks like folding and sewing? You can find any number of conceptual inventions on that front - here's one as an example:

https://blogs.nvidia.com/blog/hugging-face-lerobot-open-source-robotics/

Sure, that's a very crude folding method and it probably won't change the labor landscape in the coming months. But how fast can we evolve that space? I would imagine that 99.9% of manufacturing data points are simply lost to time because we don't track them, and we don't have the incentives to do so. Maybe the next big thing in Apparel comes from having enough video data to train the robotics to perform these tasks at scale and efficiently?

Outside of theoretical future applications, there's still so much more that can be done in this space right now. If Apparel companies can apply more technology to manufacturing, they could do things like:

  1. Deeply analyze flaws with the production process design
  2. Get near real time updates into supply chain bottlenecks
  3. Send customers ultra-detailed tracking information

If you are vertically integrated, data collection in your manufacturing process may be a killer feature for your organization. Even if you aren't vertically integrated, an investment now in partners that are inclined down this path may pay dividends later. Like manufacturing in many other spaces, automation is the future. Don't be naive and think that Apparel will always be made the same way it is today!

# How can you fix these problems?

## Lean into open source software

When I first started my career, the idea of using open source software to run an organization's data stack was amount to heresy. Thankfully, the perception of open-source software has changed alongside the evolution of cloud offerings; these two things pair well together.

If done correctly, you can create an extremely robust, resilient, and highly performant data architecture *that you own*. You are no longer beholden to how a SaaS or ERP provider thinks you should run your business, and, quite frankly, open source tooling is light years ahead of any one-stop shop that I've found.

For instance, here's a stack that I've found personal success with:

  * Infrastructure Management through Terraform
  * Job orchestration through Airflow
  * Data Modeling through dbt
  * Data Quality / Testing through dbt
  * Python as a glue language

I'd be lying if I said that this is all a "one-click" deployment, but I don't think the bar to implement part or all of this stack is all that high either.

The trend of open source software is something that affects more than just the Apparel industry as well; essentially, deploying a stack like the above just keeps you in line with larger shifts in the data space. Just recently, some of the greatest minds in data teamed up to write [https://www.vldb.org/pvldb/vol16/p2679-pedreira.pdf](The Composable Data Management System Manifesto). For this with a keen interest in data systems, this is a must read.

## Treat data quality as a shared goal

The problem with data quality is that traditional corporate stacks have done a poor job of automation. QA and MDM were often both treated as manual exercises for people to manage, which quickly become unwieldy at large organizations. Fortunately, and thanks to the ever-increasing role of open-source software within organizations, there are very capable tools that can help you manage data quality much more effectively than ever before.

With the tool of your choice, you should be able to orchestrate automated jobs that immediately flag and capture data quality issues. When you find them, you should immediately forward them to the appropriate parties to manage. This affords your organization the flexibility to have different people weave together parts of data that make up the larger picture. Done more accurately, you'll find far less "busy work" in place to achieve this goal.

Also be sure to organizationally assign ownership to different pieces of data. If data quality issues arise with fields A, B, and C in your data warehouse, the organization should know who is responsible for maintaining those fields.

Overall the process for improving this is not complicated, but rather historically neglected. With modern tooling, you can turn that history on its head and reap higher quality, more trustworthy reporting.

## Embrace Technology in Manufacturing

This last solution is a bit more open-ended because it is highly dependent upon how your company is organized and how it manages any potential manufacturing partnerships. So without offering a blanket solution, I'll bet your company can be doing more to become tech-forward with its development. If you are of the belief that Apparel will be manufactured the same way in years' time, I think you'll find many others in the industry looking to disrupt that thought. As AI becomes more accessible and storage costs go down, the barriers to solving the automation problem are breaking down as well.

So please, do whatever you can on this front to not fall behind. If you are vertically integrated, make sure you have robust production tracking software. If you think your company wants to automate more, starting taking videos of your production process to use as training data for AI models. On the flip side, if you rely on a third party manufacturers, make sure you value their technological investments as part of your sourcing strategy. Sure, it may be difficult for them to compete on price with a manufacturer that has no technological investments today, but your supply chain and data management are going to pay those costs in the long run.
