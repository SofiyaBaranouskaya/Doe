from .utils import calculate_compound_interest
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from decimal import Decimal, InvalidOperation
from .utils import calculate_angel_investment



@require_http_methods(["GET", "POST"])
def compound_calculator(request):
    defaults = {
        "initial": 5000,
        "monthly_contribution": 200,
        "annual_rate": 7,
        "years": 30,
        "cadence": "monthly",
    }

    if request.method == "GET":
        return render(request, "invest_calculator/compound.html", {
            "defaults": defaults
        })

    # POST
    try:
        initial = Decimal(str(request.POST.get("initial", "0")))
        monthly = Decimal(str(request.POST.get("monthly_contribution", "0")))
        rate_percent = Decimal(str(request.POST.get("annual_rate", "0")))
        years = int(request.POST.get("years", 0))
        cadence = request.POST.get("cadence", "monthly")

        if cadence not in ("monthly", "annually"):
            raise ValueError("Invalid cadence")

        result = calculate_compound_interest(
            initial=initial,
            monthly_contribution=monthly,
            annual_rate=rate_percent / Decimal("100"),
            years=years,
            cadence=cadence,
        )

        # AJAX-запрос
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(result)

        # Обычный POST
        return render(request, "invest_calculator/compound.html", {
            "result": result,
            "defaults": {
                "initial": float(initial),
                "monthly_contribution": float(monthly),
                "annual_rate": float(rate_percent),
                "years": years,
                "cadence": cadence,
            }
        })

    except (InvalidOperation, ValueError, TypeError) as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"error": str(e)}, status=400)
        return render(request, "invest_calculator/compound.html", {
            "error": str(e),
            "defaults": defaults
        })


@require_http_methods(["GET", "POST"])
def angel_investor_calculator(request):
    defaults = {
        "investment": 25000,
        "val_cap": 10000000,
        "interest_rate": 5.0,
        "years_until_conversion": 5.0,
        "pre_money": 15000000,
        "round_size": 5000000,
        "future_rounds": 1,
        "dilution": 20,
        "irr_time_horizon": 7,
        "security_type": "priced_round",
    }

    if request.method == "GET":
        return render(
            request,
            "invest_calculator/angel.html",
            {"defaults": defaults}
        )

    try:
        investment = Decimal(str(request.POST.get("investment", "0")))
        val_cap = Decimal(str(request.POST.get("val_cap", "0")))
        rate_percent = Decimal(str(request.POST.get("interest_rate", "0")))

        years_until_conversion = Decimal(
            str(request.POST.get("years_until_conversion", "0"))
        )

        irr_time_horizon = Decimal(
            str(request.POST.get("irr_time_horizon", "7"))
        )

        pre_money = Decimal(str(request.POST.get("pre_money", "0")))
        round_size = Decimal(str(request.POST.get("round_size", "0")))

        future_rounds = int(
            request.POST.get("future_rounds", 0)
        )

        dilution_percent = Decimal('20')

        security_type = request.POST.get(
            "security_type",
            "safe"
        )

        result = calculate_angel_investment(
            investment=investment,
            val_cap=val_cap,
            interest_rate=rate_percent / Decimal("100"),
            years_to_conversion=years_until_conversion,
            pre_money=pre_money,
            round_size=round_size,
            future_dilutive_rounds=future_rounds,
            dilution_percentage=dilution_percent,
            security_type=security_type,
            average_time_horizon=irr_time_horizon,
        )

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(result)

        return render(
            request,
            "invest_calculator/angel.html",
            {
                "result": result,
                "defaults": {
                    **defaults,
                    **request.POST.dict()
                }
            }
        )

    except (InvalidOperation, ValueError, TypeError) as e:

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"error": str(e)},
                status=400
            )

        return render(
            request,
            "invest_calculator/angel.html",
            {
                "error": str(e),
                "defaults": defaults
            }
        )