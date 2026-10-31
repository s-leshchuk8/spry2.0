resource "aws_s3_bucket" "reports" {
  bucket        = "${var.project_name}-reports-${var.environment}"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_iam_role" "reports_lambda" {
  name = "${var.project_name}-reports-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "reports_basic" {
  role       = aws_iam_role.reports_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "reports" {
  function_name = "${var.project_name}-weekly-reports"
  role          = aws_iam_role.reports_lambda.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = "dummy.zip" # шлях до вашого архіву або заглушки

  environment {
    variables = {
      REPORTS_BUCKET = aws_s3_bucket.reports.bucket
    }
  }
}

# Дозвіл для S3 викликати Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.reports.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.reports.arn
}

# Тригер S3 сповіщень
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.reports.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.reports.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_s3]
}