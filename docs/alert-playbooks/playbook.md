# Alert Playbooks

Graduated action packages per alert tier, written in control-room language.

## Tier 1 -- Watch (GSI 30-49)

**Meaning:** Elevated conditions detected; no immediate concern.

- Continue normal monitoring cadence
- Log current reserve margin and forecast accuracy

**Autonomy:** L1 (Describe) -- agent summarizes, no recommendations.

## Tier 2 -- Advisory (GSI 50-64)

**Meaning:** Conditions warrant heightened awareness and preparation.

- Increase monitoring frequency to 30-minute intervals
- Review next-24h load forecast against capacity projections
- Verify demand response program readiness

**Autonomy:** L3 (Recommend) -- agent proposes, human approves.

## Tier 3 -- Alert (GSI 65-79)

**Meaning:** Grid stress is probable within the forecast horizon.

- Activate demand response standby notifications
- Verify peaker fuel supply and start-up readiness
- Defer any planned maintenance outages in the affected BA
- Coordinate with neighboring BAs on interchange capacity

**Autonomy:** L3 (Recommend) -- agent proposes, human approves.

## Tier 4 -- Emergency Watch (GSI 80-89)

**Meaning:** Grid stress is imminent or occurring in adjacent regions.

- Pre-position emergency demand response for activation
- Notify executive operations leadership
- Verify firm load-shed rotation plans are current
- Coordinate with state emergency management if weather-driven

**Autonomy:** L4 (Act-with-veto) -- simulation only in this demonstration.

## Tier 5 -- Critical (GSI 90+)

**Meaning:** Grid reliability event is underway or unavoidable.

- Recommend immediate demand response activation
- Escalate to chief operations officer
- Prepare load-shed implementation if reserves breach minimum
- Issue public conservation appeal through established channels

**Autonomy:** L4 (Act-with-veto) -- simulation only in this demonstration.

---

*Note: These playbooks are written for demonstration purposes. In an operational
deployment, playbook actions would be developed with actual grid operators and
tailored to each BA's specific procedures and regulatory requirements.*
