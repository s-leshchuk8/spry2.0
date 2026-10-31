resource "aws_iam_role" "ai_lambda" {
  name = "${var.project_name}-ai-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ai_basic" {
  role       = aws_iam_role.ai_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "ai_bedrock_access" {
  name = "BedrockAccess"
  role = aws_iam_role.ai_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["bedrock:InvokeModel"]
      Resource = "*"
    }]
  })
}

resource "aws_lambda_function" "ai" {
  function_name = "${var.project_name}-agenda-parser"
  role          = aws_iam_role.ai_lambda.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = "dummy.zip"
  timeout       = 30

  environment {
    variables = {
      GOOGLE_CLIENT_ID     = var.google_client_id
      GOOGLE_CLIENT_SECRET = var.google_client_secret
    }
  }
}

resource "aws_lambda_function_url" "ai_url" {
  function_name      = aws_lambda_function.ai.function_name
  authorization_type = "NONE"
}