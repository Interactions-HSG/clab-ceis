# Views

The CEIS view are determined by the use cases it is demonstrating.

1. Customers compare of End of Life (EOL) scenarios with respect to their economical and environmental costs proxied by CO2eq.
2. Customers weigh delivery speed against environmental impact proxied by CO2eq.
3. Strategist review progress towards the company's goals.
4. Designer balance design, longevity, and costs of a product.


## Comparison of End of Life (EOL) Scenarios:

Sooner or later, all products reach their end of life. In this use case, owners of a product are interested in end of life scenarios of that product. They either need to start a new life cycle or dispose the product entirely. Currently, the following EoL scenarios are covered in CEIS:

1. Customer does repair on their own; CEIS assumes some cost for various processes(cleaning, etc.)
2. Customer brings it to a close by repair shop.
3. Customer send the product to Solve to perform the repair / remanufacturing.
4. Customer orders a new product from Solve.

CEIS requires a view that presents the EoL scenarios in a way that natural customer agents can easily digest the information to make corresponding decisions. To this end, they are interested in delivery time and in both environmental and ecological costs.

## Trade-off between Delivery Speed and Environmental Costs

Even in the linear economic model, delivery times are sometimes weighted against economical costs. Customers might accept higher costs if the delivery time is lower, e.g. by enrolling in a subscription model to guarantee lower delivery times (see Amazon Prime) or choosing a different vendor altogether. In the circular economy, there are additional trade-off dimensions that stem from a higher decentralization of input materials. Since they might have gone through multiple life cycles already, their remaining quality and additional costs dimensions, e.g. environmental costs proxied by CO2eq, are additionally weighted against each other.

CEIS requires a view that presents these alternatives, specifically the delivery time versus environmental costs trade-off, during the ordering process of a new product initiated by a human customer. To this end, they are interested in a list of products as well as the delivery time, both environmental and ecological costs and resulting quality.

## Strategist

A company might employ various strategies to meet environmental, economical, and circularity goals. At any given time, they want to be able to see the company's progress towards their goal. Based on the state, they want to make adjustments to the company's employed strategies. To meet economic goals, they might take circularity debt. Similar to technical debt in Software Engineering, the latter describes costs that are accepted as a workaround to achieve short term goals at the expense of higher dependency to suppliers, weakening their supply chain. However, the debt might never manifest into actual costs.

CEIS requires a view that presents progress towards the company's goals. To this end, they interested in the summed up exceeds of a circularity index threshold, the summed up economical costs, and the summed up environmental costs.

## Designer's Choice

Designers balance different aspects of the product against the design. For example, the longevity and costs of the product is impacted by their choice of materials and fabric blocks. Based on cost calculation and statistics, they make a choice a design time that must be aligned with corporate strategy.
