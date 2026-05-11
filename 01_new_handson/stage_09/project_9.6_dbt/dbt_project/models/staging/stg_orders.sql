-- stg_orders.sql
-- Staging model: clean and standardize raw orders data
-- Materialized as a view (no storage cost)

{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'orders') }}
),

cleaned as (
    select
        -- Identifiers
        order_id,
        customer_id,

        -- Dimensions
        upper(trim(product))                    as product_name,
        lower(trim(coalesce(status, 'unknown'))) as order_status,

        -- Measures
        cast(amount as double)                  as order_amount_usd,
        cast(quantity as integer)               as quantity,

        -- Dates
        cast(order_date as date)                as order_date,
        year(cast(order_date as date))          as order_year,
        month(cast(order_date as date))         as order_month,

        -- Metadata
        current_timestamp                       as _loaded_at

    from source
    where
        order_id is not null
        and amount is not null
        and amount > 0
)

select * from cleaned
