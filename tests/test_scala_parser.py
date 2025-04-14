"""Tests for the Scala parser."""

import pytest

from app.code_analysis.agents.nodes.code_chunker.parsers.scala_parser import ScalaParser


@pytest.fixture
def parser():
    """Create a Scala parser instance."""
    return ScalaParser()


@pytest.fixture
def sample_scala_code():
    """Sample Scala code with Cats Effect patterns."""
    return """
import cats.effect.{IO, Resource}
import cats.effect.std.Console
import cats.syntax.all._
import fs2.Stream
import scala.concurrent.duration._

trait Logger[F[_]] {
  def info(message: String): F[Unit]
  def error(message: String): F[Unit]
}

object Logger {
  def apply[F[_]](implicit L: Logger[F]): Logger[F] = L

  def create[F[_]: Async]: Resource[F, Logger[F]] =
    Resource.pure(
      new Logger[F] {
        def info(message: String): F[Unit] =
          Console[F].println(s"INFO: $message")

        def error(message: String): F[Unit] =
          Console[F].errorln(s"ERROR: $message")
      }
    )
}

case class User(id: String, name: String)

class UserService[F[_]: Async](logger: Logger[F]) {
  private val users = Map(
    "1" -> User("1", "Alice"),
    "2" -> User("2", "Bob")
  )

  def getUser(id: String): F[Option[User]] = {
    for {
      _ <- logger.info(s"Fetching user with id: $id")
      user <- users.get(id).pure[F]
      _ <- user.fold(
        logger.error(s"User $id not found"))(
        u => logger.info(s"Found user: ${u.name}")
      )
    } yield user
  }

  def processUsers: Stream[F, User] = {
    Stream
      .emits(users.values.toList)
      .evalMap { user =>
        logger.info(s"Processing user: ${user.name}").as(user)
      }
      .handleErrorWith { error =>
        Stream.eval(
          logger.error(s"Error processing users: ${error.getMessage}").as(
            throw error
          )
        )
      }
  }
}

object Main extends IOApp {
  def run(args: List[String]): IO[ExitCode] = {
    val program = for {
      logger <- Logger.create[IO]
      service = new UserService[IO](logger)
      result <- service.getUser("1")
        .handleErrorWith(err =>
          logger.error(s"Failed to get user: ${err.getMessage}").as(None)
        )
      _ <- result.fold(
        IO.println("User not found")
      )(user => IO.println(s"Found user: ${user.name}"))
      _ <- service.processUsers
        .evalMap(user => IO.println(s"Processed: ${user.name}"))
        .compile
        .drain
    } yield ExitCode.Success

    program.use(IO.pure)
  }
}
"""


def test_extract_imports(parser, sample_scala_code):
    """Test extraction of imports including Cats Effect imports."""
    imports = parser.extract_imports(sample_scala_code)
    assert len(imports) == 4
    assert "cats.effect.{IO, Resource}" in imports
    assert "cats.effect.std.Console" in imports
    assert "cats.syntax.all._" in imports
    assert "fs2.Stream" in imports


def test_extract_classes(parser, sample_scala_code):
    """Test extraction of classes, traits, and objects."""
    classes = parser.extract_classes(sample_scala_code)

    # Replace the class_types dictionary with direct assertions
    classes_by_name = {cls["name"]: cls["type"] for cls in classes}
    assert classes_by_name["Logger"] == "trait"
    assert classes_by_name["User"] == "class"
    assert classes_by_name["UserService"] == "class"
    assert classes_by_name["Main"] == "object"

    # Find the UserService class for detailed testing
    user_service = next(cls for cls in classes if cls["name"] == "UserService")

    # Check type parameters and constraints
    assert user_service["type_parameters"] == ["F[_]"]
    assert "Async" in user_service["type_class_constraints"][0]

    # Check methods
    methods = {method["name"]: method for method in user_service["methods"]}
    assert "getUser" in methods
    assert "processUsers" in methods

    # Check for comprehension in getUser method
    get_user_method = methods["getUser"]
    assert get_user_method["is_for_comprehension"]


def test_extract_for_comprehensions(parser, sample_scala_code):
    """Test extraction of for comprehensions."""
    classes = parser.extract_classes(sample_scala_code)
    user_service = next(cls for cls in classes if cls["name"] == "UserService")
    comprehensions = user_service["for_comprehensions"]
    assert len(comprehensions) > 0

    # Check the getUser method's for comprehension
    comp = comprehensions[0]
    assert "logger.info" in comp["generators"]
    assert "users.get" in comp["generators"]
    assert "user" in comp["yield"]


def test_extract_effect_patterns(parser, sample_scala_code):
    """Test extraction of Cats Effect specific patterns."""
    classes = parser.extract_classes(sample_scala_code)

    # Check Main object for IO patterns
    main = next(cls for cls in classes if cls["name"] == "Main")
    effect_patterns = main["effect_patterns"]

    # Verify IO constructors and operations
    constructs = [pattern["construct"] for pattern in effect_patterns]
    assert any("IO.println" in construct for construct in constructs)

    # Check error handling
    error_handling = main["error_handling"]
    handler_types = [handler["type"] for handler in error_handling]
    assert "handleErrorWith" in handler_types


def test_extract_implicits(parser, sample_scala_code):
    """Test extraction of implicit definitions."""
    classes = parser.extract_classes(sample_scala_code)
    logger_object = next(cls for cls in classes if cls["name"] == "Logger")

    # Check implicit parameters
    implicits = logger_object["implicits"]
    assert any(implicit["name"] == "L" for implicit in implicits)


def test_extract_type_signatures(parser, sample_scala_code):
    """Test extraction of type signatures with effect types."""
    classes = parser.extract_classes(sample_scala_code)
    user_service = next(cls for cls in classes if cls["name"] == "UserService")

    methods = user_service["methods"]
    get_user_method = next(m for m in methods if m["name"] == "getUser")

    assert "F[Option[User]]" in get_user_method["type_signature"]


def test_extract_error_handling(parser, sample_scala_code):
    """Test extraction of error handling patterns."""
    classes = parser.extract_classes(sample_scala_code)

    # Check UserService for error handling in Stream
    user_service = next(cls for cls in classes if cls["name"] == "UserService")
    error_handlers = user_service["error_handling"]

    handler_types = [handler["type"] for handler in error_handlers]
    assert "handleErrorWith" in handler_types
