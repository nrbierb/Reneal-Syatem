-- MySQL dump 10.13  Distrib 5.7.13, for Linux (x86_64)
--
-- Host: localhost    Database: SystemMonitor
-- ------------------------------------------------------
-- Server version	5.7.13-0ubuntu0.16.04.2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

USE SystemMonitor;

--
-- Table structure for table `ClientComputers`
--

DROP TABLE IF EXISTS `ClientComputers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ClientComputers` (
  `Index` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `MacAddress` varchar(20) NOT NULL,
  `CurrentData` tinyint(1) DEFAULT '0',
  `DataUpdateTime` bigint(20) DEFAULT NULL,
  `Memory` bigint(20) DEFAULT NULL,
  `Description` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`Index`),
  KEY `MacAddress` (`MacAddress`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ClientResourceUse`
--

DROP TABLE IF EXISTS `ClientResourceUse`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `ClientResourceUse` (
  `Index` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `Time` bigint(20) unsigned NOT NULL,
  `ClientComputerId` bigint(20) NOT NULL,
  `MbytesAvailable` float NOT NULL,
  `CpuIdle` float NOT NULL,
  PRIMARY KEY (`Index`),
  KEY `Time` (`Time`)
) ENGINE=InnoDB AUTO_INCREMENT=2193 DEFAULT CHARSET=latin1 COMMENT='Memory use in each client computer units Mbytes';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `CpuUse`
--

DROP TABLE IF EXISTS `CpuUse`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `CpuUse` (
  `Index` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `Time` bigint(20) unsigned NOT NULL,
  `PercentUserTime` float unsigned NOT NULL,
  `PercentSystemTime` float unsigned NOT NULL,
  `PercentNiceTime` float unsigned NOT NULL,
  `PercentIoWait` float unsigned NOT NULL,
  `PercentFreeTime` float unsigned NOT NULL,
  PRIMARY KEY (`Index`),
  KEY `Time` (`Time`)
) ENGINE=InnoDB AUTO_INCREMENT=3647 DEFAULT CHARSET=latin1 COMMENT='Server CPU use summed across all cores';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `MemoryUse`
--

DROP TABLE IF EXISTS `MemoryUse`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `MemoryUse` (
  `Index` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `Time` bigint(20) unsigned NOT NULL,
  `MbytesTotal` bigint(20) unsigned NOT NULL,
  `MbytesFree` bigint(20) unsigned NOT NULL,
  `MbytesUsed` bigint(20) unsigned NOT NULL,
  `MbytesCache` bigint(20) unsigned NOT NULL,
  `MbytesAvailable` bigint(20) unsigned NOT NULL,
  `MbytesSwapUsed` bigint(20) unsigned NOT NULL,
  `MbytesSwapFree` bigint(20) unsigned NOT NULL,
  PRIMARY KEY (`Index`),
  KEY `Time` (`Time`)
) ENGINE=InnoDB AUTO_INCREMENT=3613 DEFAULT CHARSET=latin1 COMMENT='Server memory and swap use';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `SummaryData`
--

DROP TABLE IF EXISTS `SummaryData`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `SummaryData` (
  `Index` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `Time` int(11) NOT NULL,
  `UserCount` int(11) NOT NULL,
  `ActiveUserCount` int(11) NOT NULL,
  `StudentCount` int(11) NOT NULL,
  `ActiveStudentCount` int(11) NOT NULL,
  `TeacherCount` int(11) NOT NULL,
  `ActiveTeacherCount` int(11) NOT NULL,
  `ClientComputerCount` int(11) NOT NULL,
  PRIMARY KEY (`Index`),
  KEY `Time` (`Time`)
) ENGINE=InnoDB AUTO_INCREMENT=3629 DEFAULT CHARSET=latin1 COMMENT='Summary counts for easier processing of simple queries';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `Users`
--

DROP TABLE IF EXISTS `Users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `Users` (
  `Index` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `UserName` varchar(45) NOT NULL,
  `Uid` int(11) NOT NULL,
  `UserType` varchar(45) NOT NULL,
  PRIMARY KEY (`Index`),
  KEY `UserName` (`UserName`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `UsersLoggedIn`
--

DROP TABLE IF EXISTS `UsersLoggedIn`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `UsersLoggedIn` (
  `Index` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `Time` int(11) NOT NULL,
  `UserId` bigint(20) NOT NULL,
  `UserActive` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`Index`),
  KEY `Time` (`Time`),
  KEY `UserId` (`UserId`)
) ENGINE=InnoDB AUTO_INCREMENT=4221 DEFAULT CHARSET=latin1 COMMENT='Users logged in by account name with flag True if not n scre';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2016-08-29 20:12:16
