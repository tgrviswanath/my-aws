-- fct_orders.sql
-- Fact table: one row per order with all relevant dimensions
-- Materialized as incremental table (only processes new orders)

{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',
        on_schema_change='sync_all_columns'
    )
}}

with orders as (
    select * from {{ ref('stg_orders') }}

    {% if is_incremental() %}
    -- Only process orders newer than the last run
    where order_date > (select max(order_date) from {{ this }})
    {% endif %}
),

final as (
    select
        -- Keys
        order_id,
        customer_id,

        -- Dimensions
        product_name,
        order_status,
        order_date,
        order_year,
        order_month,

        -- Measures
        order_amount_usd,
        quantity,
        order_amount_usd / nullif(quantity, 0) as unit_price_usd,

        -- Derived
        case
            when order_amount_usd >= 100 then 'high_value'
            when order_amount_usd >= 50  then 'medium_value'
            else 'low_value'
        end as order_tier,

        -- Metadata
        current_timestamp as _dbt_updated_at

    from orders
)

select * from final
