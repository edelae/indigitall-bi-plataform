-- Dimension: date — CTE-generated 10-year calendar (2020-2029).

with date_spine as (
    select d::date as full_date
    from generate_series(
        '2020-01-01'::date,
        '2029-12-31'::date,
        '1 day'::interval
    ) d
),

dates as (
    select
        to_char(full_date, 'YYYYMMDD')::int as date_key,
        full_date,
        extract(year from full_date)::smallint as year,
        extract(quarter from full_date)::smallint as quarter,
        extract(month from full_date)::smallint as month,
        case extract(month from full_date)
            when 1 then 'Enero'
            when 2 then 'Febrero'
            when 3 then 'Marzo'
            when 4 then 'Abril'
            when 5 then 'Mayo'
            when 6 then 'Junio'
            when 7 then 'Julio'
            when 8 then 'Agosto'
            when 9 then 'Septiembre'
            when 10 then 'Octubre'
            when 11 then 'Noviembre'
            when 12 then 'Diciembre'
        end as month_name,
        extract(week from full_date)::smallint as week_iso,
        extract(day from full_date)::smallint as day_of_month,
        extract(isodow from full_date)::smallint as day_of_week_iso,
        case extract(isodow from full_date)
            when 1 then 'Lunes'
            when 2 then 'Martes'
            when 3 then 'Miercoles'
            when 4 then 'Jueves'
            when 5 then 'Viernes'
            when 6 then 'Sabado'
            when 7 then 'Domingo'
        end as day_name,
        extract(isodow from full_date) in (6, 7) as is_weekend,
        false as is_holiday,
        null::varchar(100) as holiday_name,
        extract(year from full_date)::smallint as fiscal_year,
        extract(quarter from full_date)::smallint as fiscal_quarter,
        to_char(full_date, 'YYYY-MM') as year_month,
        to_char(full_date, 'IYYY') || '-W' || lpad(to_char(full_date, 'IW'), 2, '0') as year_week
    from date_spine
)

select * from dates
