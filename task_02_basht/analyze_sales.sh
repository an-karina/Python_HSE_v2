#!/bin/bash

file="$1"

if [[ $# -ne 1 ]]; then
  echo "Неверное количество аргументов"
  exit 1
fi

if [[ ! -e "$file" ]]; then
  echo "Файл '$file' не найден."
  exit 1
fi

awk '
{
	 if (NF < 5) {
		flag = 1
        printf "Неверное количество колонок %d\n", NR
    }

	sum += $4 * $5;
	day_rev[$1] +=  $4 * $5
	week_day[$1] = $2

	product_rev[$3] += $4 * $5
	product_qty[$3] += $5
} 
END {
	if (flag == 1) {
		exit 1
	}
	
	printf "Общая сумма продаж: %.2f\n",  sum;  

	max_day = ""
	max_rev = -1
	for (d in day_rev) {
		if (day_rev[d] > max_rev) {
			max_rev = day_rev[d]
			max_day = d
		}
	};
	printf "День с наибольшей выручкой: %s %s (сумма продаж: %.2f)\n", max_day, week_day[max_day], max_rev;


	max_p = ""
	max_qty = -1
	for (p in product_qty) {
		if (product_qty[p] > max_qty) {
			max_qty = product_qty[p]
			max_p = p
		}
	};

	printf "Популярный товар: %s (количество проданных единиц: %.0f, сумма продаж: %.2f)\n" , max_p, max_qty, product_rev[max_p] 
}
' $file