from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets, status
from .models import Transaction
from .serializers import TransactionSerializer
import pandas as pd
from sklearn.linear_model import LinearRegression

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.all()
        month = self.request.query_params.get('month', None)
        if month:
            try:
                year, month_num = month.split('-')
                queryset = queryset.filter(date__year=year, date__month=month_num)
                if not queryset.exists():
                    raise ValueError("No transactions found for this month")
            except ValueError:
                return queryset.none()
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists() and request.query_params.get('month'):
            return Response(
                {"error": "No transactions found for the selected month"},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

@api_view(['GET'])
def predict_savings(request):
    transactions = Transaction.objects.all()
    month = request.query_params.get('month', None)
    if month:
        try:
            year, month_num = month.split('-')
            transactions = transactions.filter(date__year=year, date__month=month_num)
            if not transactions.exists():
                return Response(
                    {"error": "No transactions found for this month", "predicted_savings": 0},
                    status=status.HTTP_404_NOT_FOUND
                )
        except ValueError:
            return Response(
                {"error": "Invalid month format. Use YYYY-MM", "predicted_savings": 0},
                status=status.HTTP_400_BAD_REQUEST
            )

    if not transactions.exists():
        return Response(
            {"error": "No transactions available for prediction", "predicted_savings": 0},
            status=status.HTTP_404_NOT_FOUND
        )

    df = pd.DataFrame(list(transactions.values('date', 'amount', 'type')))
    df['date'] = pd.to_datetime(df['date'])
    df['month'] = df['date'].dt.to_period('M').astype(str)

    monthly_data = df.groupby('month').apply(
        lambda x: x[x['type'] == 'income']['amount'].sum() - x[x['type'] == 'expense']['amount'].sum()
    ).reset_index(name='net_savings')

    if len(monthly_data) < 2:
        return Response(
            {"error": "Insufficient data for prediction (need at least 2 months)", "predicted_savings": 0},
            status=status.HTTP_400_BAD_REQUEST
        )

    X = pd.to_numeric(range(len(monthly_data))).reshape(-1, 1)
    y = monthly_data['net_savings'].values

    model = LinearRegression()
    model.fit(X, y)

    next_month = len(monthly_data)
    predicted_savings = model.predict([[next_month]])[0]

    return Response({"predicted_savings": round(predicted_savings, 2)})