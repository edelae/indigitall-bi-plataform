-- Dimension: contact_reason — L1/L2 hierarchy (CRIS-inspired).
-- L1 = top-level category, L2 = sub-category.
-- parent_key is NULL for L1, FK to L1 row for L2.

with seed as (
    select * from {{ ref('dim_contact_reason_seed') }}
),

final as (
    select
        s.contact_reason_key,
        s.reason_code,
        s.reason_name,
        s.parent_key,
        s.level,
        coalesce(p.reason_name, s.reason_name) as l1_name,
        case when s.level = 2 then s.reason_name end as l2_name,
        s.is_active
    from seed s
    left join seed p on p.contact_reason_key = s.parent_key
)

select * from final
